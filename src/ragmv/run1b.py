"""Study 1b retrieval multiverse (research/preregistration_study1b.md) for one dataset.

Usage:
  python -I -m ragmv.run1b --dataset squad2 --split exploratory --out experiments/E3_semantic_dense/runs/<id>
Options: --chunkings fixed-128 semantic-bp ...  --retrievers bm25 dense  --max-queries N  --device cuda
         --cache-dir DIR (embeddings; split-independent, reused between the pilot and the confirmatory run)

Output per dataset (same layout as Study 1, so the analysis code is shared): `<chunking>.npz` with scores
[n_retrievers, n_queries, n_ops, 3], words [n_retrievers, n_queries, n_ops], rr10 [n_retrievers, n_queries];
`queries.json`; `manifest.json` (code content digest, input digests, versions, encoder identity, hardware, chunk
statistics); and for semantic chunkings the chunk boundaries (`chunks_<name>.json.gz`) so every chunk can be
inspected and re-evaluated.

Embedding caches are keyed by a fingerprint of the ordered texts, the preprocessing, and the encoder's full identity
(model and tokenizer revision, maximum length, normalisation, compute dtype, device, batch size, library versions);
each entry has a JSON sidecar with its shape and file digest, and every read re-checks digest, shape, dtype and
finiteness. A corrupt or mismatching entry is an error (never silently recomputed over, never deleted). Cache files
in the historical naming scheme carry no identity and are ignored with a warning, not trusted and not deleted.
Exit code 0 = ok, 1 = the run failed (a failed manifest is kept), 2 = the run could not start.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
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
from .integrity import atomic_write_bytes, atomic_write_text, fingerprint, sha256_file, source_digest, text_list_digest
from .retrieval import RetrieverSpec, rank, tokenize
from .run import BUDGETS, KS, OPS, existing_results
from .semantic import CAP, breakpoint_chunks, chunk_text, chunk_words, clustering_chunks, sentence_units

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


class CacheError(RuntimeError):
    """An embedding cache entry is corrupt or does not match its identity; it is left in place for inspection."""


LEGACY_CACHE_PATTERNS = ("sentences_*.npz", "chunks_*.npz", "queries_*.npz")


def encoder_identity(encoder) -> dict:
    ident = getattr(encoder, "identity", None)
    if callable(ident):
        return ident()
    return {"untrusted_encoder": f"{type(encoder).__module__}.{type(encoder).__qualname__}",
            "name": getattr(encoder, "name", None)}


def warn_legacy_caches(cache: Path) -> list[str]:
    found = sorted(p.name for pat in LEGACY_CACHE_PATTERNS for p in cache.glob(pat)) if cache.exists() else []
    if found:
        print(f"WARNING: {len(found)} cache file(s) in the historical naming scheme under {cache} carry no identity "
              "and are ignored (not trusted, not deleted).", file=sys.stderr)
    return found


def cached_embeddings(cache: Path, kind: str, texts: list[str], encoder, preprocessing: dict) -> np.ndarray:
    """Embeddings of `texts` from a validated cache entry, or computed with `encoder` and stored as float16."""
    ident = {"schema": "ragmv.embcache/2", "kind": kind, "n_texts": len(texts), "texts_sha256": text_list_digest(texts),
             "preprocessing": preprocessing, "encoder": encoder_identity(encoder), "stored_dtype": "float16"}
    key = fingerprint(ident)
    npz, meta = cache / f"emb-{key}.npz", cache / f"emb-{key}.json"
    if npz.exists() or meta.exists():
        if not (npz.exists() and meta.exists()):
            raise CacheError(f"incomplete cache entry {npz.name}/{meta.name}; move both aside and rerun")
        m = json.loads(meta.read_text())
        if m.get("identity") != ident:
            raise CacheError(f"{meta}: stored identity differs from the requested one; move the entry aside")
        if sha256_file(npz) != m.get("file_sha256"):
            raise CacheError(f"{npz}: file digest does not match its sidecar (corrupt entry); move it aside")
        with np.load(npz, allow_pickle=False) as z:
            a = z["a"]
        if a.dtype != np.float16 or a.shape != (len(texts), m.get("dim")) or not np.isfinite(a).all():
            raise CacheError(f"{npz}: shape {a.shape}, dtype {a.dtype} or non-finite values do not match the sidecar")
        return a
    a = np.asarray(encoder.encode(texts))
    if a.ndim != 2 or a.shape[0] != len(texts) or not np.isfinite(a).all():
        raise CacheError(f"encoder returned shape {a.shape} or non-finite values for {len(texts)} texts")
    a = a.astype(np.float16)
    if not np.isfinite(a).all():
        raise CacheError("embeddings overflow float16")
    buf = io.BytesIO()
    np.savez_compressed(buf, a=a)
    data = buf.getvalue()
    atomic_write_bytes(npz, data)
    atomic_write_text(meta, json.dumps({"identity": ident, "dim": int(a.shape[1]), "file_sha256": hashlib.sha256(data).hexdigest()},
                                       indent=2))
    return a


def sentence_embeddings(docs, encoder, cache: Path):
    units = [sentence_units(doc) for doc in docs]
    flat = [doc.words(s, e) for doc, us in zip(docs, units) for s, e in us]
    emb = cached_embeddings(cache, "sentences", flat, encoder,
                            {"units": "ragmv.semantic.sentence_units", "cap_words": CAP,
                             "units_sha256": fingerprint([[list(u) for u in us] for us in units])}).astype(np.float32)
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
    ap.add_argument("--data-manifest", default=None)
    args = ap.parse_args(argv)
    bad = sorted(set(args.chunkings) - set(CHUNKINGS)) + sorted(set(args.retrievers) - set(RETRIEVERS))
    if bad or (args.max_queries is not None and args.max_queries < 1) or args.batch_size < 1:
        print(f"ERROR: unknown chunkings/retrievers {bad} or non-positive --max-queries/--batch-size", file=sys.stderr)
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
        queries = [q for q in queries if mask[q.doc_idx] == (args.split == "exploratory")]
    if args.max_queries:
        queries = queries[: args.max_queries]
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(args.cache_dir) / args.dataset
    legacy_caches = warn_legacy_caches(cache)
    needs_encoder = "dense" in args.retrievers or any(c.startswith("semantic") for c in args.chunkings)
    if needs_encoder and encoder is None:
        from .dense import Encoder
        encoder = Encoder(device=args.device, batch_size=args.batch_size)
    atomic_write_text(out / "queries.json", json.dumps({
        "qids": [q.qid for q in queries], "doc_idx": [q.doc_idx for q in queries],
        "n_gold_spans": [len(q.gold) for q in queries], "gold_words": [int(sum(e - s for s, e in q.gold)) for q in queries],
    }))

    status, error, chunk_stats, timings = "ok", None, [], {}
    try:
        _run_all(args, docs, queries, encoder, cache, out, chunk_stats, timings)
    except Exception as exc:  # recorded in the manifest; failed runs are kept, not deleted
        status, error = "failed", f"{type(exc).__name__}: {exc}"

    config = {
        "study": "1b", "dataset": args.dataset, "split": args.split, "max_queries": args.max_queries,
        "chunkings": args.chunkings, "retrievers": args.retrievers, "bm25": BM25.name, "ops": OPS,
        "metrics": list(METRICS), "split_seed": 20261018, "split_frac_exploratory": 0.2,
        "mode": "full" if (args.max_queries is None and sorted(args.chunkings) == sorted(CHUNKINGS)
                           and sorted(args.retrievers) == sorted(RETRIEVERS)) else "smoke",
    }
    manifest = {
        "status": status, "error": error, "config": config,
        "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
        "encoder": getattr(encoder, "name", None), "encoder_identity": encoder_identity(encoder) if encoder else None,
        "code_sha256": source_digest()["sha256"], "inputs_sha256": inputs, "ignored_legacy_caches": legacy_caches,
        "versions": _versions(), "platform": platform.platform(), "n_documents": len(docs),
        "n_queries": len(queries), "started_utc": started.isoformat(timespec="seconds"),
        "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timings": timings, "chunk_stats": chunk_stats,
    }
    atomic_write_text(out / "manifest.json", json.dumps(manifest, indent=2))
    print(json.dumps({k: manifest[k] for k in ("status", "error", "n_queries", "started_utc", "finished_utc")}))
    return 0 if status == "ok" else 1


def _run_all(args, docs, queries, encoder, cache, out, chunk_stats, timings) -> None:
    t0 = time.time()
    sent = sentence_embeddings(docs, encoder, cache) if any(c.startswith("semantic") for c in args.chunkings) else None
    timings["sentence_embeddings_s"] = round(time.time() - t0, 1)
    q_emb = None
    if "dense" in args.retrievers:
        t0 = time.time()
        q_emb = cached_embeddings(cache, "queries", [q.question for q in queries], encoder,
                                  {"field": "Query.question"}).astype(np.float32)
        timings["query_embeddings_s"] = round(time.time() - t0, 1)

    for name in args.chunkings:
        t0 = time.time()
        chunk_doc, chunk_ivs, texts = build_chunks(docs, name, sent)
        lengths = np.array([chunk_words(c) for c in chunk_ivs])
        depth = min(len(texts), max(KS) + math.ceil(max(BUDGETS) / max(1.0, float(np.percentile(lengths, 10)))) + 10)
        if name.startswith("semantic"):
            atomic_write_bytes(out / f"chunks_{name}.json.gz", gzip.compress(json.dumps(
                {"doc": chunk_doc.tolist(), "intervals": [list(map(list, c)) for c in chunk_ivs]}).encode(), mtime=0))
        scores, words, rr = [], [], []
        for r in args.retrievers:
            if r == "bm25":
                ranked = rank(tokenize(texts, True), tokenize([q.question for q in queries], True), BM25, depth)
            else:
                c_emb = cached_embeddings(cache, "chunks", texts, encoder,
                                          {"chunking": name, "text": "ragmv.semantic.chunk_text"})
                ranked = dense_rank(c_emb.astype(np.float32), q_emb, depth)
            res = evaluate_rankings(ranked, chunk_doc, chunk_ivs, queries, KS, BUDGETS)
            scores.append(res["scores"]), words.append(res["words"]), rr.append(res["rr10"])
        buf = io.BytesIO()
        np.savez_compressed(buf, scores=np.stack(scores), words=np.stack(words), rr10=np.stack(rr))
        atomic_write_bytes(out / f"{name}.npz", buf.getvalue())
        chunk_stats.append({
            "chunking": name, "n_chunks": len(texts), "depth": int(depth),
            "chunk_words_mean": float(lengths.mean()), "chunk_words_median": float(np.median(lengths)),
            "chunk_words_p10": float(np.percentile(lengths, 10)), "chunk_words_max": int(lengths.max()),
            "noncontiguous_share": float(np.mean([len(c) > 1 for c in chunk_ivs])), "seconds": round(time.time() - t0, 1),
        })
        print(json.dumps(chunk_stats[-1]), flush=True)


if __name__ == "__main__":
    sys.exit(main())
