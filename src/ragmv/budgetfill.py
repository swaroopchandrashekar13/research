"""Adaptive ranking depth, so budget-matched selection is filled whenever the corpus holds enough text.

Runners rank each query to an initial depth from the corpus 10th-percentile chunk length. That heuristic does not
guarantee that a query's top-ranked chunks contain `budget` words: if short chunks rank first, the ranked prefix runs
out before the budget is reached. `fill_to_budget` repairs this for new runs:

- the initial ranked prefix is kept exactly as it is, so count-matched (top-k) results and every budget that the
  prefix already fills are unchanged;
- a query whose prefix holds fewer than `budget` words (every chunk's full length counts, so overlapping text is
  charged as in selection) is re-ranked at twice the depth, repeatedly, and the chunks not yet in the prefix are
  appended in rank order, until the prefix holds `budget` words or the whole corpus is ranked (genuine exhaustion);
- each expansion must agree with the prefix: its first len(prefix) scores equal the prefix's scores, and every chunk
  scoring above the prefix's lowest score is already in the prefix. Otherwise RankingConsistencyError is raised.

Selection itself (truncation of the last chunk, interval order of non-contiguous chunks) is unchanged; it happens in
`evaluate` / `evaluate_multi` on the returned rows. Per query, the effective depth, the number of expansions and
whether the corpus was exhausted are returned so runs can store them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

SELECTION_RULE = "adaptive-depth/1"  # recorded in the configuration of new runs


class RankingConsistencyError(RuntimeError):
    """An expanded ranking does not extend the ranking it replaces."""


@dataclass
class FillResult:
    rows: list[np.ndarray]  # chunk indices per query, best first
    depth: np.ndarray  # int32 [n_queries]: length of each row
    expansions: np.ndarray  # int16 [n_queries]: re-rankings needed
    exhausted: np.ndarray  # bool [n_queries]: whole corpus ranked and still fewer than `budget` words

    def summary(self) -> dict:
        return {"queries_expanded": int((self.expansions > 0).sum()), "queries_exhausted": int(self.exhausted.sum()),
                "max_depth": int(self.depth.max()) if len(self.depth) else 0}


def fill_to_budget(ids: np.ndarray, scores: np.ndarray, chunk_words: np.ndarray, budget: int, n_chunks: int,
                   retrieve_one: Callable[[int, int], tuple[np.ndarray, np.ndarray]], max_rounds: int = 64) -> FillResult:
    """`ids`/`scores` [n_queries, d0]: the initial ranking, best first. `chunk_words[c]` is the length of chunk c in
    words. `retrieve_one(i, depth)` returns (ids, scores) of query i ranked to `depth` (at most n_chunks)."""
    chunk_words = np.asarray(chunk_words, dtype=np.int64)
    n_q = len(ids)
    rows = [np.asarray(ids[i], dtype=np.int64) for i in range(n_q)]
    depth = np.array([len(r) for r in rows], dtype=np.int32)
    expansions = np.zeros(n_q, dtype=np.int16)
    exhausted = np.zeros(n_q, dtype=bool)
    for i in range(n_q):
        row = rows[i]
        sc = np.asarray(scores[i], dtype=np.float64)
        words = int(chunk_words[row].sum()) if len(row) else 0
        rounds = 0
        while words < budget and len(row) < n_chunks:
            rounds += 1
            if rounds > max_rounds:
                raise RankingConsistencyError(f"query {i}: no fill after {max_rounds} expansions")
            want = min(n_chunks, max(2 * len(row), len(row) + 1))
            e_ids, e_sc = (np.asarray(a) for a in retrieve_one(i, want))
            if len(e_ids) != want or len(e_sc) != want:
                raise RankingConsistencyError(f"query {i}: asked for {want} ranked chunks, got {len(e_ids)}")
            k = len(row)
            if not np.array_equal(np.asarray(e_sc[:k], dtype=np.float64), sc):
                raise RankingConsistencyError(f"query {i}: the depth-{want} ranking does not start with the scores "
                                              f"of the depth-{k} ranking")
            prefix = set(row.tolist())
            if k and any(int(c) not in prefix for c in e_ids[np.asarray(e_sc, dtype=np.float64) > sc[-1]]):
                raise RankingConsistencyError(f"query {i}: a chunk scoring above the previous prefix is missing from it")
            extra = [j for j, c in enumerate(e_ids) if int(c) not in prefix][: want - k]
            row = np.concatenate([row, np.asarray(e_ids, dtype=np.int64)[extra]])
            sc = np.concatenate([sc, np.asarray(e_sc, dtype=np.float64)[extra]])
            words = int(chunk_words[row].sum())
        rows[i] = row
        depth[i] = len(row)
        expansions[i] = rounds
        exhausted[i] = words < budget
    return FillResult(rows, depth, expansions, exhausted)
