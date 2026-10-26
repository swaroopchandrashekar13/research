"""BM25-family retrieval over chunk texts (library: bm25s)."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product

import bm25s
import numpy as np
import Stemmer

_STEMMER = Stemmer.Stemmer("english")


@dataclass(frozen=True)
class RetrieverSpec:
    method: str  # "lucene" | "bm25+"
    k1: float
    b: float
    stem: bool  # True: English stop-words + Snowball stemming; False: lowercase only

    @property
    def name(self) -> str:
        return f"{self.method}-k{self.k1}-b{self.b}-{'stem' if self.stem else 'plain'}"


def default_retrievers() -> list[RetrieverSpec]:
    """The 16 planned retriever configurations (analysis plan §2.2)."""
    return [RetrieverSpec(m, k1, b, s) for s, m, k1, b in product((True, False), ("lucene", "bm25+"), (0.9, 1.5), (0.4, 0.75))]


def tokenize(texts: list[str], stem: bool) -> list[list[str]]:
    toks = bm25s.tokenize(
        texts,
        stopwords="en" if stem else None,
        stemmer=_STEMMER if stem else None,
        return_ids=False,
        show_progress=False,
    )
    # bm25s cannot score an empty query; an all-stop-word query gets a token that matches nothing.
    return [t if t else ["\x00empty"] for t in toks]


class Ranker:
    """One BM25 index over chunk texts; rankings at any depth reuse it. Ties keep bm25s's deterministic order."""

    def __init__(self, corpus_tokens: list[list[str]], spec: RetrieverSpec):
        self.n = len(corpus_tokens)
        self.model = bm25s.BM25(method=spec.method, k1=spec.k1, b=spec.b)
        if self.n:
            self.model.index(corpus_tokens, show_progress=False)

    def retrieve(self, query_tokens: list[list[str]], depth: int) -> tuple[np.ndarray, np.ndarray]:
        """([n_queries, d] chunk indices, [n_queries, d] scores), best first, d = min(depth, corpus size)."""
        depth = min(depth, self.n)
        if depth <= 0 or not query_tokens:
            return np.zeros((len(query_tokens), 0), np.int64), np.zeros((len(query_tokens), 0), np.float64)
        docs, scores = self.model.retrieve(query_tokens, k=depth, show_progress=False, n_threads=1)
        return np.asarray(docs, dtype=np.int64), np.asarray(scores, dtype=np.float64)


def rank(corpus_tokens: list[list[str]], query_tokens: list[list[str]], spec: RetrieverSpec, depth: int) -> np.ndarray:
    """Return an [n_queries, depth] array of chunk indices, best first (the fixed-depth ranking of the stored runs)."""
    return Ranker(corpus_tokens, spec).retrieve(query_tokens, depth)[0]


def rank_filled(corpus_tokens, query_tokens, spec: RetrieverSpec, depth: int, chunk_words, budget: int):
    """Fixed-depth ranking extended per query until `budget` words are ranked or the corpus is exhausted
    (`ragmv.budgetfill`). Returns a FillResult whose rows start with exactly the fixed-depth ranking."""
    from .budgetfill import fill_to_budget

    ranker = Ranker(corpus_tokens, spec)
    ids, scores = ranker.retrieve(query_tokens, depth)
    return fill_to_budget(ids, scores, chunk_words, budget, ranker.n,
                          lambda i, d: tuple(a[0] for a in ranker.retrieve([query_tokens[i]], d)))
