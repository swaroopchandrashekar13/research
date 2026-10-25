"""POST-HOC SENSITIVITY (2026-10-24): character-based span metrics on the *same* selections as the word metrics.

The analysis plans define the metrics over characters ("fraction of its characters retrieved"), but the stored
Study 1 / Study 1b / Tier 2 scores were computed over `\\S+` word intervals (`ragmv.evaluate`). This module scores
the selections produced by exactly the same selection functions in both ways, so any difference is attributable to
the metric definition alone:

- ``word``: the stored definition (`evaluate.span_metrics` on word intervals);
- ``char``: literal characters. A retrieved word interval [ws, we) covers characters
  [word_starts[ws], word_ends[we-1]) (its text); gold spans are the source character intervals;
- ``char_nows``: characters excluding whitespace (so whitespace between two separately retrieved chunks, which no
  chunk text contains, does not count against a gold span).

Nothing here is used by the planned analyses.
"""
from __future__ import annotations

import numpy as np

from .evaluate import LENIENT_THRESHOLD, merge, select_budget, select_count, span_metrics
from . import evaluate_multi as EM

VARIANTS = ("word", "char", "char_nows")


def nonspace_prefix(text: str) -> np.ndarray:
    """prefix[i] = number of non-whitespace characters in text[:i]."""
    ns = np.fromiter((not c.isspace() for c in text), dtype=np.int64, count=len(text))
    return np.concatenate([[0], np.cumsum(ns)])


def word_to_char_intervals(doc, word_ivs) -> list[tuple[int, int]]:
    return [(int(doc.word_starts[s]), int(doc.word_ends[e - 1])) for s, e in word_ivs if e > s]


def char_span_metrics(char_ivs, gold_chars, prefix: np.ndarray | None = None) -> tuple[float, float, float]:
    """(hit_strict, hit_lenient, coverage) over characters; with `prefix`, only non-whitespace characters count."""
    merged = merge(char_ivs)

    def size(a: int, b: int) -> int:
        return (int(prefix[b] - prefix[a]) if prefix is not None else b - a) if b > a else 0

    strict = lenient = best = 0.0
    for gs, ge in gold_chars:
        total = size(gs, ge)
        if total <= 0:
            continue
        covered = sum(size(max(s, gs), min(e, ge)) for s, e in merged)
        frac = covered / total
        best = max(best, frac)
        if covered == total:
            strict = 1.0
        if frac >= LENIENT_THRESHOLD:
            lenient = 1.0
    return strict, lenient, best


def all_variants(doc, word_ivs, gold_words, gold_chars, prefix) -> dict[str, tuple[float, float, float]]:
    civ = word_to_char_intervals(doc, word_ivs)
    return {"word": span_metrics(word_ivs, gold_words), "char": char_span_metrics(civ, gold_chars),
            "char_nows": char_span_metrics(civ, gold_chars, prefix)}


def evaluate_rankings_variants(ranked, chunk_doc, chunk_ws, chunk_we, queries, docs, ks, budgets, prefixes=None):
    """As `evaluate.evaluate_rankings` (contiguous chunks), returning float64 scores for every metric variant plus
    the float16 word scores and word counts exactly as Study 1 stored them (for the equivalence check)."""
    n_ops = len(ks) + len(budgets)
    out = {v: np.zeros((len(queries), n_ops, 3), dtype=np.float64) for v in VARIANTS}
    out["word_f16"] = np.zeros((len(queries), n_ops, 3), dtype=np.float16)
    out["words"] = np.zeros((len(queries), n_ops), dtype=np.int32)
    prefixes = prefixes if prefixes is not None else {}
    for i, q in enumerate(queries):
        doc = docs[q.doc_idx]
        prefix = prefixes.get(q.doc_idx)
        if prefix is None:
            prefix = prefixes[q.doc_idx] = nonspace_prefix(doc.text)
        row = ranked[i]
        sels = [select_count(row, chunk_doc, chunk_ws, chunk_we, q.doc_idx, k) for k in ks]
        sels += [select_budget(row, chunk_doc, chunk_ws, chunk_we, q.doc_idx, b) for b in budgets]
        for j, (iv, w) in enumerate(sels):
            res = all_variants(doc, iv, q.gold, q.gold_chars, prefix)
            for v in VARIANTS:
                out[v][i, j] = res[v]
            out["word_f16"][i, j] = res["word"]
            out["words"][i, j] = w
    return out


def evaluate_rankings_variants_multi(ranked, chunk_doc, chunk_ivs, queries, docs, ks, budgets, prefixes=None):
    """Interval-list chunks (Study 1b); same outputs as `evaluate_rankings_variants`."""
    n_ops = len(ks) + len(budgets)
    out = {v: np.zeros((len(queries), n_ops, 3), dtype=np.float64) for v in VARIANTS}
    out["word_f16"] = np.zeros((len(queries), n_ops, 3), dtype=np.float16)
    out["words"] = np.zeros((len(queries), n_ops), dtype=np.int32)
    prefixes = prefixes if prefixes is not None else {}
    for i, q in enumerate(queries):
        doc = docs[q.doc_idx]
        prefix = prefixes.get(q.doc_idx)
        if prefix is None:
            prefix = prefixes[q.doc_idx] = nonspace_prefix(doc.text)
        row = ranked[i]
        sels = [EM.select_count(row, chunk_doc, chunk_ivs, q.doc_idx, k) for k in ks]
        sels += [EM.select_budget(row, chunk_doc, chunk_ivs, q.doc_idx, b) for b in budgets]
        for j, (iv, w) in enumerate(sels):
            res = all_variants(doc, iv, q.gold, q.gold_chars, prefix)
            for v in VARIANTS:
                out[v][i, j] = res[v]
            out["word_f16"][i, j] = res["word"]
            out["words"][i, j] = w
    return out
