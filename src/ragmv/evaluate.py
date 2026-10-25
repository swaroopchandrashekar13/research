"""Selection protocols (count- vs budget-matched) and span-level retrieval metrics, all in word intervals.

Metrics per query (analysis plan §2.2, where they are defined over characters; implemented over words, see
research/ERRATA_preregistrations.md B1 and ragmv.charmetric), against gold word spans in the query's own document:
  hit_strict  = 1 if some gold span is entirely inside the union of retrieved text
  hit_lenient = 1 if some gold span has >= 50% of its words retrieved
  coverage    = max over gold spans of the fraction of its words retrieved
Exploratory: rr10 = 1 / rank of the first top-10 chunk that alone contains a gold span (0 if none).
"""
from __future__ import annotations

import numpy as np

METRICS = ("hit_strict", "hit_lenient", "coverage")
LENIENT_THRESHOLD = 0.5


def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for s, e in sorted(intervals):
        if e <= s:
            continue
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def span_metrics(retrieved: list[tuple[int, int]], gold: list[tuple[int, int]]) -> tuple[float, float, float]:
    merged = merge(retrieved)
    strict = lenient = 0.0
    best = 0.0
    for gs, ge in gold:
        covered = sum(max(0, min(e, ge) - max(s, gs)) for s, e in merged)
        frac = covered / (ge - gs)
        best = max(best, frac)
        if covered == ge - gs:
            strict = 1.0
        if frac >= LENIENT_THRESHOLD:
            lenient = 1.0
    return strict, lenient, best


def select_count(ranked, chunk_doc, chunk_ws, chunk_we, gold_doc: int, k: int) -> tuple[list[tuple[int, int]], int]:
    """Top-k chunks. Returns (intervals inside gold_doc, total words retrieved across all documents)."""
    out, words = [], 0
    for c in ranked[:k]:
        words += int(chunk_we[c] - chunk_ws[c])
        if chunk_doc[c] == gold_doc:
            out.append((int(chunk_ws[c]), int(chunk_we[c])))
    return out, words


def select_budget(ranked, chunk_doc, chunk_ws, chunk_we, gold_doc: int, budget: int) -> tuple[list[tuple[int, int]], int]:
    """Highest-ranked chunks until `budget` words; the last chunk is truncated to fit exactly.
    Overlapping text counts against the budget. Returns (intervals inside gold_doc, words used)."""
    out, remaining = [], budget
    for c in ranked:
        if remaining <= 0:
            break
        ws, we = int(chunk_ws[c]), int(chunk_we[c])
        take = min(we - ws, remaining)
        if chunk_doc[c] == gold_doc:
            out.append((ws, ws + take))
        remaining -= take
    return out, budget - remaining


def rr_at(ranked, chunk_doc, chunk_ws, chunk_we, gold_doc: int, gold, depth: int = 10) -> float:
    for r, c in enumerate(ranked[:depth], 1):
        if chunk_doc[c] != gold_doc:
            continue
        ws, we = chunk_ws[c], chunk_we[c]
        if any(ws <= gs and ge <= we for gs, ge in gold):
            return 1.0 / r
    return 0.0


def evaluate_rankings(ranked: np.ndarray, chunk_doc, chunk_ws, chunk_we, queries, ks, budgets) -> dict[str, np.ndarray]:
    """Evaluate every query at every operating point.

    Returns:
      scores    [n_queries, len(ks) + len(budgets), 3]  metric values (float16)
      words     [n_queries, len(ks) + len(budgets)]     words actually retrieved (int32)
      rr10      [n_queries]                              exploratory chunk-level RR (float16)
    """
    n_ops = len(ks) + len(budgets)
    scores = np.zeros((len(queries), n_ops, len(METRICS)), dtype=np.float16)
    words = np.zeros((len(queries), n_ops), dtype=np.int32)
    rr = np.zeros(len(queries), dtype=np.float16)
    for i, q in enumerate(queries):
        row = ranked[i]
        for j, k in enumerate(ks):
            iv, w = select_count(row, chunk_doc, chunk_ws, chunk_we, q.doc_idx, k)
            scores[i, j] = span_metrics(iv, q.gold)
            words[i, j] = w
        for j, b in enumerate(budgets, len(ks)):
            iv, w = select_budget(row, chunk_doc, chunk_ws, chunk_we, q.doc_idx, b)
            scores[i, j] = span_metrics(iv, q.gold)
            words[i, j] = w
        rr[i] = rr_at(row, chunk_doc, chunk_ws, chunk_we, q.doc_idx, q.gold)
    return {"scores": scores, "words": words, "rr10": rr}
