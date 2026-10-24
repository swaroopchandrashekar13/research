"""Selection protocols and span metrics for chunks made of one or more word intervals (Study 1b).

Same definitions as `evaluate` (Study 1); a contiguous chunk is the one-interval special case, and for such chunks
these functions return exactly what `evaluate` returns (tested). Budget selection truncates the last chunk in
document order of its intervals.
"""
from __future__ import annotations

import numpy as np

from .evaluate import METRICS, span_metrics


def select_count(ranked, chunk_doc, chunk_ivs, gold_doc: int, k: int):
    out, words = [], 0
    for c in ranked[:k]:
        for s, e in chunk_ivs[c]:
            words += e - s
            if chunk_doc[c] == gold_doc:
                out.append((s, e))
    return out, words


def select_budget(ranked, chunk_doc, chunk_ivs, gold_doc: int, budget: int):
    out, remaining = [], budget
    for c in ranked:
        if remaining <= 0:
            break
        for s, e in chunk_ivs[c]:
            if remaining <= 0:
                break
            take = min(e - s, remaining)
            if chunk_doc[c] == gold_doc:
                out.append((s, s + take))
            remaining -= take
    return out, budget - remaining


def rr_at(ranked, chunk_doc, chunk_ivs, gold_doc: int, gold, depth: int = 10) -> float:
    for r, c in enumerate(ranked[:depth], 1):
        if chunk_doc[c] == gold_doc and any(s <= gs and ge <= e for s, e in chunk_ivs[c] for gs, ge in gold):
            return 1.0 / r
    return 0.0


def evaluate_rankings(ranked: np.ndarray, chunk_doc, chunk_ivs, queries, ks, budgets) -> dict[str, np.ndarray]:
    """As `evaluate.evaluate_rankings`, for interval-list chunks."""
    n_ops = len(ks) + len(budgets)
    scores = np.zeros((len(queries), n_ops, len(METRICS)), dtype=np.float16)
    words = np.zeros((len(queries), n_ops), dtype=np.int32)
    rr = np.zeros(len(queries), dtype=np.float16)
    for i, q in enumerate(queries):
        row = ranked[i]
        for j, k in enumerate(ks):
            iv, w = select_count(row, chunk_doc, chunk_ivs, q.doc_idx, k)
            scores[i, j] = span_metrics(iv, q.gold)
            words[i, j] = w
        for j, b in enumerate(budgets, len(ks)):
            iv, w = select_budget(row, chunk_doc, chunk_ivs, q.doc_idx, b)
            scores[i, j] = span_metrics(iv, q.gold)
            words[i, j] = w
        rr[i] = rr_at(row, chunk_doc, chunk_ivs, q.doc_idx, q.gold)
    return {"scores": scores, "words": words, "rr10": rr}
