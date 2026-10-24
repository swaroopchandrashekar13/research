"""Study 1b retrieval multiverse (research/preregistration_study1b.md) for one dataset.

Usage:
  python -I -m ragmv.run1b --dataset squad2 --split exploratory --out experiments/E3_semantic_dense/runs/<id>
Options: --chunkings fixed-128 semantic-bp ...  --retrievers bm25 dense  --max-queries N  --device cuda
         --cache-dir DIR (embeddings; split-independent, reused between the pilot and the confirmatory run)

Output per dataset (same layout as Study 1, so the analysis code is shared): `<chunking>.npz` with scores
[n_retrievers, n_queries, n_ops, 3], words [n_retrievers, n_queries, n_ops], rr10 [n_retrievers, n_queries];
`queries.json`; `manifest.json` (git, versions, encoder, hardware, chunk statistics); and for semantic chunkings the
chunk boundaries (`chunks_<name>.json.gz`) so every chunk can be inspected and re-evaluated.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import numpy as np

from . import data as D
from .chunking import ChunkSpec, chunk_document
from .dense import dense_rank
from .evaluate import METRICS
from .evaluate_multi import evaluate_rankings
from .retrieval import RetrieverSpec, rank, tokenize
from .run import BUDGETS, KS, OPS, _git_sha, _git_status
from .semantic import breakpoint_chunks, chunk_text, chunk_words, clustering_chunks, sentence_units

CHUNKINGS = ("fixed-128", "fixed-256", "fixed-512", "semantic-bp", "semantic-cl")
RETRIEVERS = ("bm25", "dense")
BM25 = RetrieverSpec("lucene", 1.5, 0.75, True)  # Study 1 default retriever


def build_chunks(docs, name: str, sentence_emb=None):
    """(chunk_doc [n], chunk_ivs list of interval tuples, texts) for the whole corpus, in document order."""
    chunk_doc, chunk_ivs, texts = [], [], []
    for d_idx, doc in enumerate(docs):
        if name.startswith("fixed-"):
            chunks = [((ws, we),) for ws, we in chunk_document(doc, ChunkSpec("fixed", int(name.split("-")[1])))]
        else:
            units, emb = sentence_emb[d_idx]
            chunks = (breakpoint_chunks if name == "semantic-bp" else clustering_chunks)(units, emb)
        for c in chunks:
            chunk_doc.append(d_idx)
            chunk_ivs.append(c)
            texts.append(chunk_text(doc, c))
    return np.asarray(chunk_doc, dtype=np.int64), chunk_ivs, texts


def cached(path: Path, compute):
    """np.load a cached array, or compute, save and return it."""
    if path.exists():
        return np.load(path)["a"]
    a = compute()
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, a=a)
    return a


def sentence_embeddings(docs, encoder, cache: Path):
    units = [sentence_units(doc) for doc in docs]
    flat = [doc.words(s, e) for doc, us in zip(docs, units) for s, e in us]
    key = hashlib.sha256("\x1e".join(flat).encode()).hexdigest()[:12]
    emb = cached(cache / f"sentences_{key}.npz", lambda: encoder.encode(flat).astype(np.float16)).astype(np.float32)
    out, i = [], 0
    for us in units:
        out.append((us, emb[i: i + len(us)]))
        i += len(us)
    return out


def _versions() -> dict:
    out = {"python": sys.version.split()[0]}
    for pkg in ("numpy", "bm25s", "PyStemmer", "torch", "transformers", "sentence-transformers"):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def main(argv=None, encoder=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=sorted(D.LOADERS))
    ap.add_argument("--split", required=True, choices=["exploratory", "confirmatory", "all"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--data-root", default="data/raw")
    ap.add_argument("--chunkings", nargs="*", default=list(CHUNKINGS))
    ap.add_argument("--retrievers", nargs="*", default=list(RETRIEVERS))
    ap.add_argument("--max-queries", type=int)
    ap.add_argument("--device")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--cache-dir", default="/tmp/ragmv_cache")
    args = ap.parse_args(argv)
    assert set(args.chunkings) <= set(CHUNKINGS) and set(args.retrievers) <= set(RETRIEVERS)

    started = datetime.now(timezone.utc)
    docs, queries = D.load(args.dataset, Path(args.data_root))
    mask = D.split_documents(len(docs))
    if args.split != "all":
        queries = [q for q in queries if mask[q.doc_idx] == (args.split == "exploratory")]
    if args.max_queries:
        queries = queries[: args.max_queries]
    out = Path(args.out) / args.dataset
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache_dir) / args.dataset
    needs_encoder = "dense" in args.retrievers or any(c.startswith("semantic") for c in args.chunkings)
    if needs_encoder and encoder is None:
        from .dense import Encoder
        encoder = Encoder(device=args.device, batch_size=args.batch_size)
    (out / "queries.json").write_text(json.dumps({
        "qids": [q.qid for q in queries], "doc_idx": [q.doc_idx for q in queries],
        "n_gold_spans": [len(q.gold) for q in queries], "gold_words": [int(sum(e - s for s, e in q.gold)) for q in queries],
    }))

    t0 = time.time()
    sent = sentence_embeddings(docs, encoder, cache) if any(c.startswith("semantic") for c in args.chunkings) else None
    timings = {"sentence_embeddings_s": round(time.time() - t0, 1)}
    q_emb = None
    if "dense" in args.retrievers:
        t0 = time.time()
        q_all = [q.question for q in queries]
        q_emb = cached(cache / f"queries_{args.split}_{hashlib.sha256(json.dumps(q_all).encode()).hexdigest()[:12]}.npz",
                       lambda: encoder.encode(q_all).astype(np.float16)).astype(np.float32)
        timings["query_embeddings_s"] = round(time.time() - t0, 1)

    chunk_stats = []
    for name in args.chunkings:
        t0 = time.time()
        chunk_doc, chunk_ivs, texts = build_chunks(docs, name, sent)
        lengths = np.array([chunk_words(c) for c in chunk_ivs])
        depth = min(len(texts), max(KS) + math.ceil(max(BUDGETS) / max(1.0, float(np.percentile(lengths, 10)))) + 10)
        if name.startswith("semantic"):
            with gzip.open(out / f"chunks_{name}.json.gz", "wt") as f:
                json.dump({"doc": chunk_doc.tolist(), "intervals": [list(map(list, c)) for c in chunk_ivs]}, f)
        scores, words, rr = [], [], []
        for r in args.retrievers:
            if r == "bm25":
                ranked = rank(tokenize(texts, True), tokenize([q.question for q in queries], True), BM25, depth)
            else:
                key = hashlib.sha256("\x1e".join(texts).encode()).hexdigest()[:12]  # stale caches never match
                c_emb = cached(cache / f"chunks_{name}_{key}.npz", lambda: encoder.encode(texts).astype(np.float16))
                ranked = dense_rank(c_emb.astype(np.float32), q_emb, depth)
            res = evaluate_rankings(ranked, chunk_doc, chunk_ivs, queries, KS, BUDGETS)
            scores.append(res["scores"]), words.append(res["words"]), rr.append(res["rr10"])
        np.savez_compressed(out / f"{name}.npz", scores=np.stack(scores), words=np.stack(words), rr10=np.stack(rr))
        chunk_stats.append({
            "chunking": name, "n_chunks": len(texts), "depth": int(depth),
            "chunk_words_mean": float(lengths.mean()), "chunk_words_median": float(np.median(lengths)),
            "chunk_words_p10": float(np.percentile(lengths, 10)), "chunk_words_max": int(lengths.max()),
            "noncontiguous_share": float(np.mean([len(c) > 1 for c in chunk_ivs])), "seconds": round(time.time() - t0, 1),
        })
        print(json.dumps(chunk_stats[-1]), flush=True)

    config = {
        "study": "1b", "dataset": args.dataset, "split": args.split, "max_queries": args.max_queries,
        "chunkings": args.chunkings, "retrievers": args.retrievers, "bm25": BM25.name, "ops": OPS,
        "metrics": list(METRICS), "split_seed": 20261018, "split_frac_exploratory": 0.2,
    }
    manifest = {
        "status": "ok", "config": config,
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "encoder": getattr(encoder, "name", None), "git": _git_sha(), "git_status": _git_status(),
        "versions": _versions(), "platform": platform.platform(), "n_documents": len(docs),
        "n_queries": len(queries), "started_utc": started.isoformat(timespec="seconds"),
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timings": timings, "chunk_stats": chunk_stats,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in ("status", "n_queries", "started_utc", "finished_utc")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
