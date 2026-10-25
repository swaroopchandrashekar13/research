"""POST-HOC SENSITIVITY (2026-10-24, not part of the analysis plans): character-based metrics on re-executed BM25 selections.

The stored runs keep per-query scores, word counts and RR@10 but not the rankings or selected intervals, so the
selections cannot be reconstructed from storage. This module therefore **re-executes** BM25 retrieval (deterministic
on CPU) with the stored configuration and, for every query, chunking, retriever and operating point, scores the same
selection with the stored word metric and with two character metrics (`ragmv.charmetric`). Selection equivalence is
verified before anything is attributed to the metric: the re-executed word scores (float16, as stored) and word
counts must equal the stored arrays element for element.

Outputs (a new directory; the historical runs are only read):
  <out>/<variant>/<dataset>/{manifest.json, queries.json, <chunking>.npz}  for variant in word64, char, char_nows
  <out>/equivalence.json   per dataset and chunking: elements compared and mismatches (scores, words)
`word64` is the stored word metric without float16 rounding (isolates the storage-precision effect).

Usage:
  python -I -m ragmv.posthoc study1  --stored <E1 run> --data-root data/raw --out <new dir> [--workers 4]
  python -I -m ragmv.posthoc study1b --stored <E3 run> --data-root data/raw --out <new dir>   # BM25 arm only
Dense retrieval (bge-m3) is not re-executed (GPU embeddings of the full corpora), so the character-metric impact
on dense-retrieval results is not quantified by this module.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import multiprocessing as mp
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import data as D
from .charmetric import VARIANTS, evaluate_rankings_variants, evaluate_rankings_variants_multi
from .chunking import ChunkSpec, chunk_document, default_specs
from .fetch import verify_consumed
from .integrity import atomic_write_bytes, atomic_write_text, source_digest
from .retrieval import RetrieverSpec, default_retrievers, rank, tokenize
from .run import BUDGETS, KS
from .semantic import chunk_text, chunk_words

OUT_VARIANTS = ("word64", "char", "char_nows")
_STATE: dict = {}


def _npz_bytes(**arrays) -> bytes:
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return buf.getvalue()


def _load_dataset(stored: Path, dataset: str, data_root: Path):
    inputs = verify_consumed(dataset, data_root)
    docs, queries = D.load(dataset, data_root)
    q = json.loads((stored / dataset / "queries.json").read_text())
    by_id = {x.qid: x for x in queries}
    sel = [by_id[i] for i in q["qids"]]
    if [x.doc_idx for x in sel] != q["doc_idx"]:
        raise RuntimeError(f"{dataset}: stored doc_idx differ from the loaded data")
    return docs, sel, inputs


def _write_variant_runs(out: Path, dataset: str, stored: Path, arrays: dict, config_extra: dict, inputs: dict,
                        retrievers: list[str], chunk_names: list[str]) -> None:
    m = json.loads((stored / dataset / "manifest.json").read_text())
    q = json.loads((stored / dataset / "queries.json").read_text())
    for variant in OUT_VARIANTS:
        d = out / variant / dataset
        d.mkdir(parents=True, exist_ok=True)
        cfg = dict(m["config"])
        cfg.update(config_extra, retrievers=retrievers, chunkings=chunk_names, metric_variant=variant, posthoc=True)
        man = {"status": "ok", "error": None, "config": cfg,
               "config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
               "posthoc": "POST-HOC SENSITIVITY 2026-10-24: re-executed BM25 selections, metric variant " + variant,
               "source_run_config_sha256": m.get("config_sha256"), "code_sha256": source_digest()["sha256"],
               "inputs_sha256": inputs, "n_documents": m.get("n_documents"), "n_queries": m.get("n_queries"),
               "chunk_stats": [s for s in m.get("chunk_stats", []) if s["chunking"] in chunk_names],
               "versions": {}, "platform": "", "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        if "n_documents_exploratory" in m:
            man["n_documents_exploratory"] = m["n_documents_exploratory"]
        atomic_write_text(d / "manifest.json", json.dumps(man, indent=2))
        atomic_write_text(d / "queries.json", json.dumps(q))
        for c in chunk_names:
            atomic_write_bytes(d / f"{c}.npz", _npz_bytes(scores=arrays[c][variant], words=arrays[c]["words"],
                                                          rr10=np.zeros(arrays[c]["words"].shape[:2], np.float16)))


# ----------------------------------------------------------------------------------------------------- Study 1
def _study1_chunking(spec_name: str) -> dict:
    docs, queries, retrievers, stored_npz, depth_want = (_STATE[k] for k in ("docs", "queries", "retrievers", "npz", "depth"))
    spec = next(s for s in default_specs() if s.name == spec_name)
    cd, cws, cwe, texts = [], [], [], []
    for d_idx, doc in enumerate(docs):
        for ws, we in chunk_document(doc, spec):
            cd.append(d_idx), cws.append(ws), cwe.append(we), texts.append(doc.words(ws, we))
    cd, cws, cwe = (np.asarray(a, dtype=np.int64) for a in (cd, cws, cwe))
    lengths = cwe - cws
    depth = min(len(texts), max(KS) + math.ceil(max(BUDGETS) / max(1.0, float(np.percentile(lengths, 10)))) + 10)
    corpus_tok = {stem: tokenize(texts, stem) for stem in {r.stem for r in retrievers}}
    query_tok = {stem: tokenize([q.question for q in queries], stem) for stem in corpus_tok}
    out = {v: [] for v in VARIANTS + ("word_f16", "words")}
    prefixes: dict = {}
    for r in retrievers:
        ranked = rank(corpus_tok[r.stem], query_tok[r.stem], r, depth)
        res = evaluate_rankings_variants(ranked, cd, cws, cwe, queries, docs, KS, BUDGETS, prefixes)
        for k in out:
            out[k].append(res[k])
    arrays = {k: np.stack(v) for k, v in out.items()}
    with np.load(stored_npz[spec_name], allow_pickle=False) as z:
        s_scores, s_words = z["scores"], z["words"]
    eq = {"depth": int(depth), "depth_matches_manifest": int(depth) == depth_want[spec_name],
          "elements_scores": int(s_scores.size), "mismatch_scores": int((arrays["word_f16"] != s_scores).sum()),
          "elements_words": int(s_words.size), "mismatch_words": int((arrays["words"] != s_words).sum())}
    return {"chunking": spec_name, "equivalence": eq,
            "arrays": {"word64": arrays["word"], "char": arrays["char"], "char_nows": arrays["char_nows"],
                       "words": arrays["words"]}}


def study1(stored: Path, data_root: Path, out: Path, workers: int = 4, datasets=None) -> dict:
    report = {}
    for dataset in datasets or ("squad2", "covidqa", "cuad", "qasper"):
        t0 = time.time()
        docs, queries, inputs = _load_dataset(stored, dataset, data_root)
        m = json.loads((stored / dataset / "manifest.json").read_text())
        names = m["config"]["retrievers"]
        by_name = {r.name: r for r in default_retrievers()}
        retrievers = [by_name[n] for n in names]
        chunk_names = m["config"]["chunkings"]
        _STATE.update(docs=docs, queries=queries, retrievers=retrievers,
                      npz={c: stored / dataset / f"{c}.npz" for c in chunk_names},
                      depth={s["chunking"]: s["depth"] for s in m["chunk_stats"]})
        if workers > 1:
            with mp.get_context("fork").Pool(workers) as pool:
                results = pool.map(_study1_chunking, chunk_names)
        else:
            results = [_study1_chunking(c) for c in chunk_names]
        arrays = {r["chunking"]: r["arrays"] for r in results}
        _write_variant_runs(out, dataset, stored, arrays, {}, inputs, names, chunk_names)
        report[dataset] = {r["chunking"]: r["equivalence"] for r in results}
        report[dataset]["_seconds"] = round(time.time() - t0, 1)
        print(json.dumps({dataset: {"seconds": report[dataset]["_seconds"],
                                    "mismatches": sum(v["mismatch_scores"] + v["mismatch_words"]
                                                      for k, v in report[dataset].items() if not k.startswith("_"))}}),
              flush=True)
    return report


# ----------------------------------------------------------------------------------------------------- Study 1b
def study1b_bm25(stored: Path, data_root: Path, out: Path, datasets=None) -> dict:
    bm25 = RetrieverSpec("lucene", 1.5, 0.75, True)
    report = {}
    for dataset in datasets or ("squad2", "covidqa", "cuad", "qasper"):
        t0 = time.time()
        docs, queries, inputs = _load_dataset(stored, dataset, data_root)
        m = json.loads((stored / dataset / "manifest.json").read_text())
        r_idx = m["config"]["retrievers"].index("bm25")
        depth_want = {s["chunking"]: s["depth"] for s in m["chunk_stats"]}
        chunk_names = m["config"]["chunkings"]
        arrays, report[dataset] = {}, {}
        prefixes: dict = {}
        for name in chunk_names:
            if name.startswith("fixed-"):
                ivs = [((ws, we),) for doc in docs for ws, we in chunk_document(doc, ChunkSpec("fixed", int(name.split("-")[1])))]
                cd = [d for d, doc in enumerate(docs) for _ in chunk_document(doc, ChunkSpec("fixed", int(name.split("-")[1])))]
            else:
                obj = json.loads(gzip.decompress((stored / dataset / f"chunks_{name}.json.gz").read_bytes()))
                cd = obj["doc"]
                ivs = [tuple(tuple(x) for x in c) for c in obj["intervals"]]
            cd = np.asarray(cd, dtype=np.int64)
            texts = [chunk_text(docs[d], c) for d, c in zip(cd, ivs)]
            lengths = np.array([chunk_words(c) for c in ivs])
            depth = min(len(texts), max(KS) + math.ceil(max(BUDGETS) / max(1.0, float(np.percentile(lengths, 10)))) + 10)
            ranked = rank(tokenize(texts, True), tokenize([q.question for q in queries], True), bm25, depth)
            res = evaluate_rankings_variants_multi(ranked, cd, ivs, queries, docs, KS, BUDGETS, prefixes)
            with np.load(stored / dataset / f"{name}.npz", allow_pickle=False) as z:
                s_scores, s_words = z["scores"][r_idx], z["words"][r_idx]
            report[dataset][name] = {
                "depth": int(depth), "depth_matches_manifest": int(depth) == depth_want[name],
                "elements_scores": int(s_scores.size), "mismatch_scores": int((res["word_f16"] != s_scores).sum()),
                "elements_words": int(s_words.size), "mismatch_words": int((res["words"] != s_words).sum())}
            arrays[name] = {"word64": res["word"][None], "char": res["char"][None], "char_nows": res["char_nows"][None],
                            "words": res["words"][None]}
        _write_variant_runs(out, dataset, stored, arrays, {}, inputs, ["bm25"], chunk_names)
        report[dataset]["_seconds"] = round(time.time() - t0, 1)
        print(json.dumps({dataset: report[dataset]}), flush=True)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("study", choices=("study1", "study1b"))
    ap.add_argument("--stored", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--datasets", nargs="*")
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists() and any(out.iterdir()):
        print(f"ERROR: {out} is not empty; post-hoc outputs go to a new directory", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if args.study == "study1":
        rep = study1(Path(args.stored), Path(args.data_root), out, args.workers, args.datasets)
    else:
        rep = study1b_bm25(Path(args.stored), Path(args.data_root), out, args.datasets)
    rep["_meta"] = {"study": args.study, "stored_run": str(args.stored), "seconds": round(time.time() - t0, 1),
                    "code_sha256": source_digest()["sha256"], "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "label": "POST-HOC SENSITIVITY (not part of the analysis plans); new BM25 execution"}
    atomic_write_text(out / "equivalence.json", json.dumps(rep, indent=2))
    bad = sum(v["mismatch_scores"] + v["mismatch_words"] for d, cs in rep.items() if not d.startswith("_")
              for c, v in cs.items() if not c.startswith("_"))
    print(f"selection-equivalence mismatches: {bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
