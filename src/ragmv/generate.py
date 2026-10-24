"""Tier 2 (exploratory): does the retrieval-level protocol reversal carry over to generated answers?

Usage:
  python -I -m ragmv.generate --dataset squad2 --out experiments/E2_generation/runs/<id> --model <gemini-model> [--dry-run]
  python -I -m ragmv.generate --list-models          # models available to the key (needs the key)
  python -I -m ragmv.generate --backend llama --model <key of LOCAL_MODELS> --dataset squad2 --out <dir>

The API key is read ONLY from the environment variable RAGMV_GEMINI_API_KEY and is never written anywhere.
The llama backend runs a pinned open-weight GGUF model on CPU (llama.cpp), greedy decoding; the file is downloaded
from its Hugging Face commit and its SHA-256 is checked before use.
Results are appended to `<out>/<dataset>/generations.jsonl`; reruns skip finished rows, so a run interrupted by a
daily quota simply resumes the next day. Scoring: SQuAD-style exact match and token F1 (max over gold answers).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import string
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

from . import data as D
from .chunking import chunk_document, default_specs
from .evaluate import span_metrics
from .retrieval import default_retrievers, rank, tokenize
from .run import _git_sha, _git_status

KEY_ENV = "RAGMV_GEMINI_API_KEY"
CHUNKINGS = ("fixed-128", "fixed-512", "paragraph-256", "fixed-256")  # claims P1 and S3-256
OPS = (("count", 5), ("budget", 1024))
RETRIEVER = "lucene-k1.5-b0.75-stem"
SAMPLE_SEED = 20261019
SYSTEM = (
    "Answer the question using only the numbered passages. Reply with the shortest answer that is fully supported "
    "by the passages, copying the wording from them where possible. If the passages do not contain the answer, "
    "reply exactly: unanswerable"
)
MAX_OUTPUT_TOKENS = 256
# Pinned open-weight readers: (Hugging Face repo, commit, file, SHA-256, thinking model?)
LOCAL_MODELS = {
    "qwen2.5-1.5b-instruct-q4_k_m": ("Qwen/Qwen2.5-1.5B-Instruct-GGUF", "91cad51170dc346986eccefdc2dd33a9da36ead9",
                                     "qwen2.5-1.5b-instruct-q4_k_m.gguf",
                                     "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e", False),
    "qwen3-4b-q4_k_m": ("Qwen/Qwen3-4B-GGUF", "bc640142c66e1fdd12af0bd68f40445458f3869b", "Qwen3-4B-Q4_K_M.gguf",
                        "7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5", True),
}


# ----------------------------------------------------------------------------- selection with text
def select_passages(ranked, chunk_doc, chunk_ws, chunk_we, mode: str, param: int) -> list[tuple[int, int, int]]:
    """(doc, ws, we) of the selected chunks in rank order; budget mode truncates the last chunk to fit exactly."""
    out, remaining = [], param
    for i, c in enumerate(ranked):
        ws, we = int(chunk_ws[c]), int(chunk_we[c])
        if mode == "count":
            if i >= param:
                break
            out.append((int(chunk_doc[c]), ws, we))
        else:
            if remaining <= 0:
                break
            take = min(we - ws, remaining)
            out.append((int(chunk_doc[c]), ws, ws + take))
            remaining -= take
    return out


def build_prompt(question: str, passages: list[str]) -> str:
    body = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(passages, 1))
    return f"Passages:\n{body}\n\nQuestion: {question}\nAnswer:"


# ----------------------------------------------------------------------------- SQuAD-style scoring
def normalize_answer(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in set(string.punctuation))
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def exact_match(pred: str, golds: list[str]) -> float:
    return float(any(normalize_answer(pred) == normalize_answer(g) for g in golds))


def token_f1(pred: str, golds: list[str]) -> float:
    best = 0.0
    p = normalize_answer(pred).split()
    for g in golds:
        t = normalize_answer(g).split()
        common = Counter(p) & Counter(t)
        same = sum(common.values())
        if not p or not t:
            best = max(best, float(p == t))
        elif same:
            prec, rec = same / len(p), same / len(t)
            best = max(best, 2 * prec * rec / (prec + rec))
    return best


# ----------------------------------------------------------------------------- jobs
def sample_queries(queries, mask, n: int, seed: int = SAMPLE_SEED):
    """n confirmatory queries, seeded; deterministic given the dataset."""
    pool = [q for q in queries if not mask[q.doc_idx]]
    rng = random.Random(seed)
    return sorted(rng.sample(pool, min(n, len(pool))), key=lambda q: q.qid)


def build_jobs(docs, queries) -> list[dict]:
    """One job per (query, chunking, operating point), with the retrieved text and its retrieval metrics."""
    spec_by_name = {s.name: s for s in default_specs()}
    retr = next(r for r in default_retrievers() if r.name == RETRIEVER)
    jobs = []
    for cname in CHUNKINGS:
        spec = spec_by_name[cname]
        cd, cws, cwe, texts = [], [], [], []
        for d_idx, doc in enumerate(docs):
            for ws, we in chunk_document(doc, spec):
                cd.append(d_idx), cws.append(ws), cwe.append(we), texts.append(doc.words(ws, we))
        cd, cws, cwe = (np.asarray(a) for a in (cd, cws, cwe))
        ranked = rank(tokenize(texts, retr.stem), tokenize([q.question for q in queries], retr.stem), retr, depth=64)
        for qi, q in enumerate(queries):
            for mode, param in OPS:
                sel = select_passages(ranked[qi], cd, cws, cwe, mode, param)
                passages = [docs[d].words(ws, we) for d, ws, we in sel]
                in_doc = [(ws, we) for d, ws, we in sel if d == q.doc_idx]
                prompt = build_prompt(q.question, passages)
                jobs.append({
                    "job_id": f"{q.qid}|{cname}|{mode}{param}", "qid": q.qid, "chunking": cname,
                    "op": f"{mode}{param}", "answers": q.answers, "prompt": prompt,
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "context_words": sum(we - ws for _, ws, we in sel),
                    "retrieval": dict(zip(("hit_strict", "hit_lenient", "coverage"), span_metrics(in_doc, q.gold))),
                })
    return jobs


def done_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    out = set()
    for row in read_rows(path):
        if row.get("status") == "ok":
            out.add(row["job_id"])
    return out


def read_rows(path: Path) -> list[dict]:
    """Rows of a generations file; a half-written line (process killed mid-write, e.g. a Colab disconnect) is skipped."""
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def chatml(system: str, user: str, no_think: bool) -> str:
    """Qwen chat format, written out so the exact model input is fixed; an empty think block disables thinking."""
    s = f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"
    return s + ("<think>\n\n</think>\n\n" if no_think else "")


def local_model_path(name: str, model_dir: Path) -> Path:
    from huggingface_hub import hf_hub_download

    repo, commit, fname, sha, _ = LOCAL_MODELS[name]
    path = Path(hf_hub_download(repo, fname, revision=commit, local_dir=model_dir / repo.replace("/", "__")))
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    if h.hexdigest() != sha:
        raise RuntimeError(f"{path}: SHA-256 mismatch")
    return path


def hardware_tag(n_gpu_layers: int) -> str:
    """Where a local generation ran; greedy outputs can differ between CPU and GPU builds, so every row records it."""
    import platform
    import subprocess
    from importlib.metadata import version

    gpu = "cpu"
    if n_gpu_layers and platform.system() == "Darwin":  # Apple silicon: llama.cpp offloads via Metal
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout
        gpu = f"metal {chip.strip() or 'apple'}"
    elif n_gpu_layers:
        try:
            gpu = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True,
                                 text=True, check=True).stdout.strip().splitlines()[0]
        except (OSError, subprocess.CalledProcessError, IndexError):
            gpu = "gpu-unknown"
    return f"{gpu}|{platform.machine()}|llama_cpp_python {version('llama_cpp_python')}|n_gpu_layers {n_gpu_layers}"


def call_local(llm, name: str, prompt: str, n_ctx: int) -> dict:
    repo, commit, fname, _, thinking = LOCAL_MODELS[name]
    text = chatml(SYSTEM, prompt, no_think=thinking)
    n_prompt = len(llm.tokenize(text.encode(), add_bos=False, special=True))
    if n_prompt + MAX_OUTPUT_TOKENS > n_ctx:
        return {"status": "error", "error": f"context overflow: {n_prompt} prompt tokens"}
    t0 = time.time()
    out = llm.create_completion(text, max_tokens=MAX_OUTPUT_TOKENS, temperature=0.0, top_k=1, seed=7,
                                stop=["<|im_end|>"])
    choice = out["choices"][0]
    return {
        "status": "ok", "response": choice["text"].strip(), "latency_s": round(time.time() - t0, 2),
        "model_version": f"{repo}@{commit[:12]}/{fname}", "finish_reason": choice["finish_reason"],
        "usage": {"prompt_token_count": out["usage"]["prompt_tokens"],
                  "candidates_token_count": out["usage"]["completion_tokens"]},
    }


def call_model(client, model: str, prompt: str, thinking_level: str | None = "minimal", max_retries: int = 6):
    from google.genai import types  # imported lazily so dry runs need no SDK

    think = types.ThinkingConfig(thinking_level=thinking_level) if thinking_level else None
    cfg = types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.0, seed=7,
                                      max_output_tokens=MAX_OUTPUT_TOKENS, thinking_config=think)
    delay = 10.0
    for attempt in range(max_retries):
        try:
            t0 = time.time()
            resp = client.models.generate_content(model=model, contents=prompt, config=cfg)
            usage = getattr(resp, "usage_metadata", None)
            return {
                "status": "ok", "response": (resp.text or "").strip(), "latency_s": round(time.time() - t0, 2),
                "model_version": getattr(resp, "model_version", None),  # served model; aliases can redirect
                "finish_reason": str(resp.candidates[0].finish_reason) if resp.candidates else None,
                "usage": usage.model_dump(exclude_none=True) if usage else None,
            }
        except Exception as exc:  # noqa: BLE001 - record and back off; the message never contains the key
            full = str(exc)
            msg = f"{type(exc).__name__}: {full[:300]}"
            quota_day = "PerDay" in full or "per day" in full.lower()  # quota id sits past the truncation point
            if quota_day or attempt == max_retries - 1:
                return {"status": "quota_exhausted" if quota_day else "error", "error": msg}
            time.sleep(delay)
            delay = min(delay * 2, 120)
    return {"status": "error", "error": "unreachable"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", choices=sorted(D.LOADERS))
    ap.add_argument("--out")
    ap.add_argument("--backend", choices=("gemini", "llama"), default="gemini")
    ap.add_argument("--model")
    ap.add_argument("--model-dir", default=os.path.expanduser("~/.cache/ragmv-models"))
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--n-ctx", type=int, default=8192)
    ap.add_argument("--n-gpu-layers", type=int, default=0, help="llama backend: -1 offloads all layers to the GPU")
    ap.add_argument("--thinking-level", default="minimal", help="Gemini thinking level; 'none' sends no setting")
    ap.add_argument("--per-dataset", type=int, default=50)
    ap.add_argument("--rpm", type=float, default=8.0, help="requests per minute (stay under the key's limit)")
    ap.add_argument("--max-calls", type=int, default=10_000)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--data-root", default="data/raw")
    args = ap.parse_args(argv)
    thinking = None if args.thinking_level == "none" else args.thinking_level

    key = os.environ.get(KEY_ENV)
    if args.list_models:
        if not key:
            sys.exit(f"{KEY_ENV} is not set")
        from google import genai
        client = genai.Client(api_key=key)  # keep a reference: the SDK closes its HTTP client when collected
        for m in client.models.list():
            print(m.name)
        return 0
    if not (args.dataset and args.out):
        sys.exit("--dataset and --out are required")

    docs, queries = D.load(args.dataset, Path(args.data_root))
    mask = D.split_documents(len(docs))
    sample = sample_queries(queries, mask, args.per_dataset)
    jobs = build_jobs(docs, sample)
    out = Path(args.out) / args.dataset
    out.mkdir(parents=True, exist_ok=True)
    (out / "jobs_meta.json").write_text(json.dumps({
        "n_jobs": len(jobs), "qids": [q.qid for q in sample], "chunkings": CHUNKINGS, "ops": [f"{m}{p}" for m, p in OPS],
        "retriever": RETRIEVER, "sample_seed": SAMPLE_SEED, "system_prompt": SYSTEM, "model": args.model,
        "backend": args.backend, "local_model": LOCAL_MODELS.get(args.model) if args.backend == "llama" else None,
        "threads": args.threads if args.backend == "llama" else None,
        "thinking_level": thinking if args.backend == "gemini" else "off (empty think block)",
        "temperature": 0.0, "seed": 7, "max_output_tokens": MAX_OUTPUT_TOKENS,
        "git": _git_sha(), "git_status": _git_status(), "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mean_context_words": float(np.mean([j["context_words"] for j in jobs])),
    }, indent=2))
    if args.dry_run:
        print(json.dumps({"dataset": args.dataset, "jobs": len(jobs),
                          "mean_context_words": round(float(np.mean([j["context_words"] for j in jobs])), 1)}))
        return 0
    if args.backend == "llama":
        if args.model not in LOCAL_MODELS:
            sys.exit(f"--model must be one of {sorted(LOCAL_MODELS)}")
        from llama_cpp import Llama
        llm = Llama(model_path=str(local_model_path(args.model, Path(args.model_dir))), n_ctx=args.n_ctx,
                    n_threads=args.threads, n_gpu_layers=args.n_gpu_layers, seed=7, verbose=False)
        call = lambda prompt: call_local(llm, args.model, prompt, args.n_ctx)  # noqa: E731
        gap = 0.0
        hardware = hardware_tag(args.n_gpu_layers)
    else:
        if not key:
            sys.exit(f"{KEY_ENV} is not set; set it in the environment settings (never in chat or files)")
        if not args.model:
            sys.exit("--model is required (see --list-models)")
        from google import genai
        client = genai.Client(api_key=key)
        call = lambda prompt: call_model(client, args.model, prompt, thinking)  # noqa: E731
        gap = 60.0 / args.rpm
        hardware = "gemini-api"
    path = out / "generations.jsonl"
    finished = done_ids(path)
    todo = [j for j in jobs if j["job_id"] not in finished][: args.max_calls]
    t_start, n_prev = time.time(), len(jobs) - len(todo)
    with open(path, "a") as f:
        for i, j in enumerate(todo, 1):
            if i in (4, 11) or i % 20 == 0:  # early estimates first, then every 20 jobs
                per_job = (time.time() - t_start) / (i - 1)
                print(f"{args.dataset}: {n_prev + i - 1}/{len(jobs)} done, {per_job:.1f} s/job, "
                      f"~{per_job * (len(todo) - i + 1) / 60:.0f} min left for this dataset", flush=True)
            t0 = time.time()
            res = call(j["prompt"])
            row = {k: v for k, v in j.items() if k != "prompt"}
            row.update(res, model=args.model, hardware=hardware,
                       called_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            if res["status"] == "ok":
                row["em"] = exact_match(res["response"], j["answers"])
                row["f1"] = token_f1(res["response"], j["answers"])
            f.write(json.dumps(row) + "\n")
            f.flush()
            if res["status"] == "quota_exhausted":
                print("daily quota exhausted; rerun later to resume")
                break
            time.sleep(max(0.0, gap - (time.time() - t0)))
    n_ok = len(done_ids(path))
    print(json.dumps({"dataset": args.dataset, "jobs": len(jobs), "completed": n_ok}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
