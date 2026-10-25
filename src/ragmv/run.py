"""Run the retrieval multiverse for one dataset and write per-query results plus a provenance manifest.

Usage:
  python -I -m ragmv.run --dataset squad2 --split exploratory --out experiments/E1_retrieval_multiverse/runs/<id>
Options: --chunkings fixed-128 fixed-512 ...   --retrievers lucene-k1.5-b0.75-stem ...
         --max-queries N (smoke tests)   --workers 4   --data-manifest data/MANIFEST.yaml

The exact input files are checked against the manifest's SHA-256 digests before loading. An output dataset
directory that already holds results is never overwritten (the command stops). A run restricted by --max-queries,
--chunkings or --retrievers is labelled `mode: smoke` in its manifest and cannot be analysed as confirmatory or
exploratory. The manifest records a content digest of the code (`code_sha256`), not a version-control commit.
Each query is ranked to an initial depth from the corpus 10th-percentile chunk length and, if that prefix holds fewer
words than the largest budget, ranked deeper until it does or the corpus is exhausted (`ragmv.budgetfill`); every
<chunking>.npz stores the effective depth, the number of expansions and the exhaustion flag per retriever and query.
Exit code 0 = ok, 1 = the run failed (a failed manifest is kept), 2 = the run could not start.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import numpy as np

from . import data as D
from .chunking import chunk_document, default_specs
from .evaluate import METRICS, evaluate_rankings
from .budgetfill import SELECTION_RULE
from .integrity import atomic_write_text, source_digest
from .provenance import RUN_SCHEMA
from .retrieval import default_retrievers, rank_filled, tokenize

KS = (1, 3, 5, 10)
BUDGETS = (128, 256, 512, 1024, 2048)
OPS = [f"k{k}" for k in KS] + [f"B{b}" for b in BUDGETS]

_STATE: dict = {}


def existing_results(out: Path) -> list[str]:
    """Result files already present in a dataset output directory (a run never overwrites them)."""
    if not out.exists():
        return []
    return sorted(p.name for p in out.iterdir() if p.name in ("manifest.json", "queries.json") or p.suffix in (".npz", ".gz"))


def _versions() -> dict:
    out = {"python": sys.version.split()[0]}
    for pkg in ("numpy", "bm25s", "PyStemmer", "scipy", "statsmodels"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def _run_chunking(spec_name: str) -> dict:
    docs, queries, retrievers, out_dir = _STATE["docs"], _STATE["queries"], _STATE["retrievers"], _STATE["out"]
    spec = next(s for s in default_specs() if s.name == spec_name)
    t0 = time.time()
    chunk_doc, chunk_ws, chunk_we, texts = [], [], [], []
    for d_idx, doc in enumerate(docs):
        for ws, we in chunk_document(doc, spec):
            chunk_doc.append(d_idx)
            chunk_ws.append(ws)
            chunk_we.append(we)
            texts.append(doc.words(ws, we))
    chunk_doc, chunk_ws, chunk_we = map(lambda a: np.asarray(a, dtype=np.int64), (chunk_doc, chunk_ws, chunk_we))
    lengths = chunk_we - chunk_ws
    # Depth large enough to fill the largest budget with short chunks (10th-percentile length).
    depth = min(len(texts), max(KS) + math.ceil(max(BUDGETS) / max(1.0, float(np.percentile(lengths, 10)))) + 10)
    corpus_tok = {stem: tokenize(texts, stem) for stem in {r.stem for r in retrievers}}
    query_tok = {stem: tokenize([q.question for q in queries], stem) for stem in corpus_tok}
    scores, words, rr, depths, expansions, exhausted, fill = [], [], [], [], [], [], {}
    for r in retrievers:
        res_fill = rank_filled(corpus_tok[r.stem], query_tok[r.stem], r, depth, lengths, max(BUDGETS))
        res = evaluate_rankings(res_fill.rows, chunk_doc, chunk_ws, chunk_we, queries, KS, BUDGETS)
        scores.append(res["scores"])
        words.append(res["words"])
        rr.append(res["rr10"])
        depths.append(res_fill.depth), expansions.append(res_fill.expansions), exhausted.append(res_fill.exhausted)
        fill[r.name] = res_fill.summary()
    tmp = out_dir / f".{spec_name}.npz.part"
    with open(tmp, "wb") as f:
        np.savez_compressed(f, scores=np.stack(scores), words=np.stack(words), rr10=np.stack(rr), depth=np.stack(depths),
                            expansions=np.stack(expansions), exhausted=np.stack(exhausted))
    tmp.replace(out_dir / f"{spec_name}.npz")
    return {
        "chunking": spec_name, "n_chunks": int(len(texts)), "depth": int(depth), "budget_fill": fill,
        "chunk_words_mean": float(lengths.mean()), "chunk_words_median": float(np.median(lengths)),
        "chunk_words_p10": float(np.percentile(lengths, 10)), "seconds": round(time.time() - t0, 1),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=sorted(D.LOADERS))
    ap.add_argument("--split", required=True, choices=["exploratory", "confirmatory", "all"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-root", default="data/raw")
    ap.add_argument("--chunkings", nargs="*")
    ap.add_argument("--retrievers", nargs="*")
    ap.add_argument("--max-queries", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--data-manifest", default=None)
    args = ap.parse_args(argv)
    if args.max_queries is not None and args.max_queries < 1 or args.workers < 1:
        print("ERROR: --max-queries and --workers must be positive", file=sys.stderr)
        return 2
    unknown = sorted(set(args.chunkings or []) - {s.name for s in default_specs()}) + \
        sorted(set(args.retrievers or []) - {r.name for r in default_retrievers()})
    if unknown:
        print(f"ERROR: unknown chunkings/retrievers {unknown}", file=sys.stderr)
        return 2
    out = Path(args.out) / args.dataset
    if existing_results(out):
        print(f"ERROR: {out} already holds results {existing_results(out)}; runs never overwrite results. Use a new "
              "--out directory.", file=sys.stderr)
        return 2
    from .fetch import IntegrityError, verify_consumed
    try:
        inputs = verify_consumed(args.dataset, Path(args.data_root), args.data_manifest)
    except IntegrityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    started = datetime.now(timezone.utc)
    docs, queries = D.load(args.dataset, Path(args.data_root))
    mask = D.split_documents(len(docs))
    if args.split != "all":
        want = args.split == "exploratory"
        queries = [q for q in queries if mask[q.doc_idx] == want]
    if args.max_queries:
        queries = queries[: args.max_queries]
    specs = [s.name for s in default_specs() if not args.chunkings or s.name in args.chunkings]
    retrievers = [r for r in default_retrievers() if not args.retrievers or r.name in args.retrievers]
    out.mkdir(parents=True, exist_ok=True)
    atomic_write_text(out / "queries.json", json.dumps({
        "qids": [q.qid for q in queries], "doc_idx": [q.doc_idx for q in queries],
        "n_gold_spans": [len(q.gold) for q in queries],
        "gold_words": [int(sum(e - s for s, e in q.gold)) for q in queries],
    }))
    _STATE.update(docs=docs, queries=queries, retrievers=retrievers, out=out)
    status, chunk_stats, error = "ok", [], None
    try:
        if args.workers > 1:
            with mp.get_context("fork").Pool(args.workers) as pool:
                chunk_stats = pool.map(_run_chunking, specs)
        else:
            chunk_stats = [_run_chunking(s) for s in specs]
    except Exception as exc:  # recorded in the manifest; failed runs are kept, not deleted
        status, error = "failed", f"{type(exc).__name__}: {exc}"
    config = {
        "study": "1", "selection": SELECTION_RULE, "dataset": args.dataset, "split": args.split,
        "max_queries": args.max_queries,
        "chunkings": specs, "retrievers": [r.name for r in retrievers], "ops": OPS, "metrics": list(METRICS),
        "split_seed": 20261018, "split_frac_exploratory": 0.2,
        "mode": "smoke" if (args.max_queries or args.chunkings or args.retrievers) else "full",
    }
    manifest = {
        "schema": RUN_SCHEMA, "status": status, "error": error,
        "config": config,
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "code_sha256": source_digest()["sha256"], "inputs_sha256": inputs,
        "versions": _versions(), "platform": platform.platform(),
        "n_documents": len(docs), "n_documents_exploratory": int(mask.sum()), "n_queries": len(queries),
        "started_utc": started.isoformat(timespec="seconds"),
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chunk_stats": chunk_stats,
        "peak_rss_mib": {
            "self": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "children": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024, 1),
        },
    }
    atomic_write_text(out / "manifest.json", json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in ("status", "error", "n_queries", "started_utc", "finished_utc")}))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
