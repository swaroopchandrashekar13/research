"""Tier 2 (exploratory): does the retrieval-level protocol reversal carry over to generated answers?

Usage:
  python -I -m ragmv.generate --dataset squad2 --out experiments/E2_generation/runs/<id> --model <gemini-model> [--dry-run]
  python -I -m ragmv.generate --list-models          # models available to the key (needs the key)
  python -I -m ragmv.generate --backend llama --model <key of LOCAL_MODELS> --dataset squad2 --out <dir>

The API key is read ONLY from the environment variable RAGMV_GEMINI_API_KEY and is never written anywhere.
The llama backend runs a pinned open-weight GGUF model on CPU (llama.cpp), greedy decoding; the file is downloaded
from its Hugging Face commit and its SHA-256 is checked before use.
Results are appended to `<out>/<dataset>/generations.jsonl` (further segments `generations.seg-NNN.jsonl` are opened
whenever the previous one does not end cleanly, so a record is never appended onto an interrupted line). Reruns skip
finished jobs, so a run interrupted by a quota or a session limit resumes later, but only if everything that can
change an output is identical: the run's identity (dataset bytes, sample, jobs and prompts, code, model and file
digest, full prompt template, decoding, context limit, hardware mode) is fingerprinted into `run_identity.json` when
the run starts and a mismatching resume is refused without touching the directory. `jobs_meta.json` keeps the
original start metadata; every session is appended to `sessions.jsonl`. A lock prevents concurrent writers.
`--dry-run` builds the jobs and prints the plan without writing anything.

Exit codes: 0 all jobs of the dataset have a successful row; 3 the run is incomplete (quota, --max-calls or failed
jobs remain); 2 the run cannot start (integrity, identity, lock or usage error).
Scoring: SQuAD-style exact match and token F1 (max over gold answers).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import random
import re
import string
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import data as D
from .chunking import chunk_document, default_specs
from .evaluate import span_metrics
from .integrity import (RunLock, RunLockError, canonical_json, create_exclusive, diff_fields, environment_record,
                        fingerprint, source_digest, text_list_digest)
from .budgetfill import SELECTION_RULE
from .retrieval import default_retrievers, rank, rank_filled, tokenize

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
OUTCOME_MODULES = ["chunking.py", "data.py", "evaluate.py", "generate.py", "retrieval.py"]  # code that shapes outputs
EXIT_COMPLETE, EXIT_INCOMPLETE, EXIT_CANNOT_START = 0, 3, 2
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


def build_jobs(docs, queries, adaptive: bool = True) -> list[dict]:
    """One job per (query, chunking, operating point), with the retrieved text and its retrieval metrics.

    New runs rank to depth 64 and extend a query's ranking until the 1,024-word budget is filled or the corpus is
    exhausted (`ragmv.budgetfill`). `adaptive=False` reproduces the fixed depth-64 ranking of the stored runs."""
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
        tok_c, tok_q = tokenize(texts, retr.stem), tokenize([q.question for q in queries], retr.stem)
        if adaptive:
            budget = max(p for m, p in OPS if m == "budget")
            ranked = rank_filled(tok_c, tok_q, retr, 64, cwe - cws, budget).rows
        else:
            ranked = rank(tok_c, tok_q, retr, depth=64)
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


class JsonlIntegrityError(ValueError):
    """A generations log is malformed; the message gives the file and line."""


@dataclass
class JsonlScan:
    """Result of reading one or more JSONL segments without modifying them."""
    rows: list[dict] = field(default_factory=list)  # parsed records, in file order
    raw_lines: int = 0  # physical lines read, including a tolerated fragment
    rejected: list[str] = field(default_factory=list)  # "path:line: reason" for each tolerated incomplete tail
    unterminated: bool = False  # the last segment does not end with a newline (never append to it)


def scan_jsonl(path: Path, recover_tail: bool = False, scan: JsonlScan | None = None) -> JsonlScan:
    """Strict JSONL reader. Any malformed interior record is an error (with path and line). An incomplete *final*
    record (no trailing newline, not valid JSON: a writer killed mid-line) is tolerated only with `recover_tail`, and
    is then reported in `rejected`; the file itself is never altered."""
    scan = scan or JsonlScan()
    data = Path(path).read_bytes()
    if not data:
        scan.unterminated = False
        return scan
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JsonlIntegrityError(f"{path}: not valid UTF-8 ({exc})") from exc
    ends_nl = text.endswith("\n")
    lines = text.split("\n")
    if ends_nl:
        lines = lines[:-1]
    for i, line in enumerate(lines, 1):
        scan.raw_lines += 1
        last = i == len(lines)
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("record is not a JSON object")
        except ValueError as exc:
            if last and not ends_nl:
                if not recover_tail:
                    raise JsonlIntegrityError(
                        f"{path}:{i}: incomplete final record (interrupted write). Nothing was changed. Rerun with "
                        "--recover-incomplete-tail to ignore it explicitly; resumed rows then go to a new segment "
                        "file and the damaged original is kept as it is.") from exc
                scan.rejected.append(f"{path}:{i}: incomplete final record ignored ({len(line)} bytes)")
                continue
            raise JsonlIntegrityError(f"{path}:{i}: malformed JSON record ({exc}); refusing to read a damaged log. "
                                      "Inspect the line; never edit the original in place.") from exc
        scan.rows.append(row)
    scan.unterminated = not ends_nl
    return scan


def segment_paths(out_dir: Path) -> list[Path]:
    """generations.jsonl followed by generations.seg-NNN.jsonl segments, in order."""
    first = Path(out_dir) / "generations.jsonl"
    segs = sorted(Path(out_dir).glob("generations.seg-[0-9][0-9][0-9].jsonl"))
    return ([first] if first.exists() else []) + segs


def scan_run(out_dir: Path, recover_tail: bool = False) -> JsonlScan:
    scan = JsonlScan()
    for p in segment_paths(out_dir):
        scan_jsonl(p, recover_tail, scan)
    return scan


def summarize_rows(rows: list[dict], where: str = "") -> dict:
    """Accepted = the last ok row per job; superseded = every other row of a job that has rows. Checks that each
    job_id is the deterministic key qid|chunking|op of its own row."""
    last_ok, seen = {}, collections.Counter()
    ok_rows = 0
    for i, r in enumerate(rows):
        for k in ("job_id", "qid", "chunking", "op", "status"):
            if k not in r:
                raise JsonlIntegrityError(f"{where} record {i + 1}: missing field {k!r}")
        if r["job_id"] != f"{r['qid']}|{r['chunking']}|{r['op']}":
            raise JsonlIntegrityError(f"{where} record {i + 1}: job_id {r['job_id']!r} does not match qid|chunking|op")
        seen[r["job_id"]] += 1
        if r["status"] == "ok":
            ok_rows += 1
            last_ok[r["job_id"]] = r
    accepted = len(last_ok)
    return {"accepted_rows": list(last_ok.values()), "counts": {
        "complete": ok_rows, "accepted": accepted, "superseded": len(rows) - accepted,
        "duplicate_ok": ok_rows - accepted,
        "status_counts": dict(collections.Counter(r["status"] for r in rows))}}


def done_ids(path: Path, recover_tail: bool = True) -> set[str]:
    """Job IDs with a successful row. `path` is a dataset run directory or a generations file. Progress counters
    call this with the tail tolerated (explicitly); the generator itself decides through --recover-incomplete-tail."""
    path = Path(path)
    if path.is_dir():
        scan = scan_run(path, recover_tail)
    elif path.exists():
        scan = scan_jsonl(path, recover_tail)
        for seg in sorted(path.parent.glob("generations.seg-[0-9][0-9][0-9].jsonl")) if path.name == "generations.jsonl" else []:
            scan_jsonl(seg, recover_tail, scan)
    else:
        return set()
    return {r["job_id"] for r in scan.rows if r.get("status") == "ok"}


def read_rows(path: Path, recover_tail: bool = False) -> list[dict]:
    """Rows of a generations file (strict; see `scan_jsonl`)."""
    return scan_jsonl(path, recover_tail).rows


def append_segment(out_dir: Path) -> Path:
    """The file new rows are appended to: the last segment if it ends cleanly with a newline, else a new segment, so
    a new record is never written onto an unfinished fragment and damaged originals stay untouched."""
    segs = segment_paths(out_dir)
    if not segs:
        return Path(out_dir) / "generations.jsonl"
    last = segs[-1]
    data = last.read_bytes()
    if not data or data.endswith(b"\n"):
        return last
    n = len(segs) + 1
    return Path(out_dir) / f"generations.seg-{n:03d}.jsonl"


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


def run_identity(args, dataset: str, sample, jobs, inputs: dict, hardware: str) -> dict:
    """Everything that can change an output of this run; any difference forbids appending to the run directory."""
    local = LOCAL_MODELS.get(args.model) if args.backend == "llama" else None
    if args.backend == "llama":
        template = chatml(SYSTEM, "{user}", no_think=bool(local and local[4]))
        decoding = {"temperature": 0.0, "top_k": 1, "seed": 7, "max_tokens": MAX_OUTPUT_TOKENS, "stop": ["<|im_end|>"]}
        model = {"name": args.model, "repo": local[0] if local else None, "revision": local[1] if local else None,
                 "file": local[2] if local else None, "file_sha256": local[3] if local else None}
        context = {"n_ctx": args.n_ctx}
    else:
        template = "system_instruction=SYSTEM; contents={user}"
        decoding = {"temperature": 0.0, "seed": 7, "max_output_tokens": MAX_OUTPUT_TOKENS,
                    "thinking_level": None if args.thinking_level == "none" else args.thinking_level}
        model = {"name": args.model}
        context = {}
    env = environment_record()["packages"]
    return {
        "schema": "ragmv.generate/run-identity/1",
        "dataset": dataset, "inputs_sha256": inputs,
        "sample": {"seed": SAMPLE_SEED, "per_dataset": args.per_dataset, "qids_sha256": text_list_digest([q.qid for q in sample])},
        "design": {"chunkings": list(CHUNKINGS), "ops": [f"{m}{p}" for m, p in OPS], "retriever": RETRIEVER,
                   "selection": SELECTION_RULE},
        "jobs": {"n": len(jobs), "sha256": text_list_digest([f"{j['job_id']}\t{j['prompt_sha256']}" for j in jobs])},
        "prompt": {"system": SYSTEM, "template": template, "template_sha256": fingerprint(template)},
        "backend": args.backend, "model": model, "decoding": decoding, "context": context,
        "hardware": {"tag": hardware, "n_gpu_layers": args.n_gpu_layers if args.backend == "llama" else None,
                     "threads": args.threads if args.backend == "llama" else None},
        "code": source_digest(modules=OUTCOME_MODULES),
        "packages": {k: env.get(k) for k in ("numpy", "bm25s", "PyStemmer", "llama_cpp_python", "google-genai")},
    }


def _fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return EXIT_CANNOT_START


def _hardware_for(args) -> str:
    return hardware_tag(args.n_gpu_layers) if args.backend == "llama" else "gemini-api"


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
    ap.add_argument("--dry-run", action="store_true", help="build jobs and print the plan; writes nothing")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--data-root", default="data/raw")
    ap.add_argument("--data-manifest", default=None, help="manifest whose digests the inputs must match")
    ap.add_argument("--recover-incomplete-tail", action="store_true",
                    help="tolerate (and report) an interrupted final record; new rows go to a new segment")
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
    if args.per_dataset < 1 or args.max_calls < 0 or args.n_ctx < 1:
        return _fail("--per-dataset and --n-ctx must be positive and --max-calls non-negative")
    if args.backend == "llama" and args.model not in LOCAL_MODELS:
        return _fail(f"--model must be one of {sorted(LOCAL_MODELS)}")
    if args.backend == "gemini" and not args.model and not args.dry_run:
        return _fail("--model is required (see --list-models)")

    from .fetch import IntegrityError, verify_consumed
    try:
        inputs = verify_consumed(args.dataset, Path(args.data_root), args.data_manifest)
    except IntegrityError as exc:
        return _fail(str(exc))
    docs, queries = D.load(args.dataset, Path(args.data_root))
    mask = D.split_documents(len(docs))
    sample = sample_queries(queries, mask, args.per_dataset)
    jobs = build_jobs(docs, sample)
    out = Path(args.out) / args.dataset
    hardware = "dry-run" if args.dry_run else _hardware_for(args)
    identity = run_identity(args, args.dataset, sample, jobs, inputs, hardware)
    plan = {"dataset": args.dataset, "jobs": len(jobs), "identity_sha256": fingerprint(identity),
            "mean_context_words": round(float(np.mean([j["context_words"] for j in jobs])), 1)}
    if args.dry_run:  # no file or directory is created
        print(json.dumps(plan))
        return 0

    id_path = out / "run_identity.json"
    if out.exists() and any(p.name != "run.lock" for p in out.iterdir()) and not id_path.exists():
        return _fail(f"{out} holds a run without run_identity.json (historical or foreign run). It is left untouched; "
                     "start a new --out directory instead of extending it.")
    if id_path.exists():
        stored = json.loads(id_path.read_text())
        if stored.get("identity") != identity:
            diffs = diff_fields(stored.get("identity", {}), identity)
            return _fail(f"{out} was started with a different run identity; refusing to resume (nothing was "
                         "modified). Differences:\n  " + "\n  ".join(diffs[:30]))
    try:
        lock = RunLock(out)
        lock.__enter__()
    except RunLockError as exc:
        return _fail(str(exc))
    try:
        return _generate(args, out, jobs, sample, identity, thinking, key, hardware)
    finally:
        lock.__exit__(None, None, None)


def _generate(args, out, jobs, sample, identity, thinking, key, hardware) -> int:
    id_path = out / "run_identity.json"
    if not id_path.exists():
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        create_exclusive(id_path, json.dumps({"identity_sha256": fingerprint(identity), "created_utc": started,
                                              "identity": identity}, indent=2))
        create_exclusive(out / "jobs_meta.json", json.dumps({
            "n_jobs": len(jobs), "qids": [q.qid for q in sample], "chunkings": CHUNKINGS,
            "ops": [f"{m}{p}" for m, p in OPS], "retriever": RETRIEVER, "sample_seed": SAMPLE_SEED,
            "system_prompt": SYSTEM, "model": args.model, "backend": args.backend,
            "local_model": LOCAL_MODELS.get(args.model) if args.backend == "llama" else None,
            "threads": args.threads if args.backend == "llama" else None,
            "thinking_level": thinking if args.backend == "gemini" else "off (empty think block)",
            "temperature": 0.0, "seed": 7, "max_output_tokens": MAX_OUTPUT_TOKENS,
            "code_sha256": identity["code"]["sha256"], "identity_sha256": fingerprint(identity),
            "started_utc": started, "mean_context_words": float(np.mean([j["context_words"] for j in jobs])),
        }, indent=2))
    try:
        scan = scan_run(out, args.recover_incomplete_tail)
        summary = summarize_rows(scan.rows, str(out))
    except JsonlIntegrityError as exc:
        return _fail(str(exc))
    for msg in scan.rejected:
        print(f"WARNING: {msg}; the file is unchanged and new rows go to a new segment", file=sys.stderr)
    finished = {r["job_id"] for r in summary["accepted_rows"]}
    known = {j["job_id"] for j in jobs}
    if finished - known:
        return _fail(f"{len(finished - known)} logged job IDs are not part of this run's jobs")
    session = {"session_start_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "pid": os.getpid(),
               "identity_sha256": fingerprint(identity), "already_done": len(finished),
               "rejected_tail_records": scan.rejected, "argv_flags": {"max_calls": args.max_calls,
                                                                       "recover_incomplete_tail": args.recover_incomplete_tail}}
    if args.backend == "llama":
        from llama_cpp import Llama
        llm = Llama(model_path=str(local_model_path(args.model, Path(args.model_dir))), n_ctx=args.n_ctx,
                    n_threads=args.threads, n_gpu_layers=args.n_gpu_layers, seed=7, verbose=False)
        call = lambda prompt: call_local(llm, args.model, prompt, args.n_ctx)  # noqa: E731
        gap = 0.0
    else:
        if not key:
            return _fail(f"{KEY_ENV} is not set; set it in the environment settings (never in chat or files)")
        from google import genai
        client = genai.Client(api_key=key)
        call = lambda prompt: call_model(client, args.model, prompt, thinking)  # noqa: E731
        gap = 60.0 / args.rpm
    todo = [j for j in jobs if j["job_id"] not in finished][: args.max_calls]
    t_start, n_prev = time.time(), len(jobs) - len(todo)
    path = append_segment(out)
    attempted = errors = 0
    quota = False
    with open(path, "a", encoding="utf-8") as f:
        for i, j in enumerate(todo, 1):
            if i in (4, 11) or i % 20 == 0:  # early estimates first, then every 20 jobs
                per_job = (time.time() - t_start) / (i - 1)
                print(f"{args.dataset}: {n_prev + i - 1}/{len(jobs)} done, {per_job:.1f} s/job, "
                      f"~{per_job * (len(todo) - i + 1) / 60:.0f} min left for this dataset", flush=True)
            t0 = time.time()
            res = call(j["prompt"])
            attempted += 1
            row = {k: v for k, v in j.items() if k != "prompt"}
            row.update(res, model=args.model, hardware=hardware,
                       called_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            if res["status"] == "ok":
                row["em"] = exact_match(res["response"], j["answers"])
                row["f1"] = token_f1(res["response"], j["answers"])
            else:
                errors += 1
            f.write(json.dumps(row) + "\n")
            f.flush()
            os.fsync(f.fileno())
            if res["status"] == "quota_exhausted":
                quota = True
                print("daily quota exhausted; rerun later to resume")
                break
            time.sleep(max(0.0, gap - (time.time() - t0)))
    n_ok = len(done_ids(out, recover_tail=args.recover_incomplete_tail))
    code = EXIT_COMPLETE if n_ok == len(jobs) else EXIT_INCOMPLETE
    session.update(session_end_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), segment=path.name,
                   attempted=attempted, errors=errors, quota_exhausted=quota, completed=n_ok, exit_code=code)
    with open(out / "sessions.jsonl", "a", encoding="utf-8") as f:
        f.write(canonical_json(session) + "\n")
    print(json.dumps({"dataset": args.dataset, "jobs": len(jobs), "completed": n_ok, "exit_code": code}))
    return code


if __name__ == "__main__":
    sys.exit(main())
