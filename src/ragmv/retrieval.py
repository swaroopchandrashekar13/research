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
    """The 16 pre-registered retriever configurations (preregistration §2.2)."""
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


def rank(corpus_tokens: list[list[str]], query_tokens: list[list[str]], spec: RetrieverSpec, depth: int) -> np.ndarray:
    """Return an [n_queries, depth] array of chunk indices, best first. Ties keep bm25s's deterministic order."""
    model = bm25s.BM25(method=spec.method, k1=spec.k1, b=spec.b)
    model.index(corpus_tokens, show_progress=False)
    depth = min(depth, len(corpus_tokens))
    docs, _ = model.retrieve(query_tokens, k=depth, show_progress=False, n_threads=1)
    return np.asarray(docs, dtype=np.int64)
