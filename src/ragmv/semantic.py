"""Study 1b semantic chunkers (research/preregistration_study1b.md §3.1).

A chunk is a tuple of half-open word intervals inside one document. Breakpoint chunks are contiguous (one interval);
clustering chunks may be non-contiguous (several intervals, in document order, adjacent sentences merged).
Sentence embeddings are passed in, so the chunkers are pure numpy and independent of the encoder.
"""
from __future__ import annotations

import numpy as np

from .chunking import _pack, fixed_windows, sentence_bounds
from .data import Document

CAP = 512  # maximum words per chunk (both chunkers)
BP_PERCENTILE = 95  # breakpoint: cosine distance above this percentile of the document's distances
CL_LAMBDA = 0.5  # clustering: weight of the positional distance
CL_THRESHOLD = 0.5  # clustering: pairs farther apart than this are never merged

Chunk = tuple[tuple[int, int], ...]


def sentence_units(doc: Document, cap: int = CAP) -> list[tuple[int, int]]:
    """Study 1 sentence splitter over the whole document; a sentence longer than `cap` words is split into
    fixed windows of `cap` words, so every unit fits in a chunk."""
    out = []
    for s, e in sentence_bounds(doc, 0, doc.n_words) if doc.n_words else []:
        out.extend(fixed_windows(s, e, cap) if e - s > cap else [(s, e)])
    return out


def _unit(emb: np.ndarray) -> np.ndarray:
    emb = np.asarray(emb, dtype=np.float64)
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    return emb / np.where(norms == 0, 1.0, norms)


def breakpoint_chunks(units: list[tuple[int, int]], emb: np.ndarray, cap: int = CAP,
                      percentile: float = BP_PERCENTILE) -> list[Chunk]:
    """Split between consecutive sentences whose cosine distance exceeds the document's `percentile`-th percentile
    (the LangChain/LlamaIndex 'percentile' breakpoint rule); groups longer than `cap` words are re-packed by sentence."""
    if not units:
        return []
    groups, start = [], 0
    if len(units) > 1:
        e = _unit(emb)
        dist = 1.0 - np.sum(e[:-1] * e[1:], axis=1)
        threshold = np.percentile(dist, percentile)
        for i in np.flatnonzero(dist > threshold):
            groups.append(units[start: i + 1])
            start = i + 1
    groups.append(units[start:])
    out: list[Chunk] = []
    for g in groups:
        if g[-1][1] - g[0][0] <= cap:
            out.append(((g[0][0], g[-1][1]),))
        else:
            out.extend(((s, e),) for s, e in _pack(g, cap, lambda a, b: fixed_windows(a, b, cap)))
    return out


def clustering_chunks(units: list[tuple[int, int]], emb: np.ndarray, cap: int = CAP, lam: float = CL_LAMBDA,
                      threshold: float = CL_THRESHOLD) -> list[Chunk]:
    """Qu et al.'s single-linkage clustering: d = lam * |a - b| / n + (1 - lam) * (1 - max(cos, 0)); pairs are
    merged in increasing distance (ties by index) while the merged cluster has at most `cap` words; merging stops at
    `threshold`. Unmerged sentences stay single chunks."""
    n = len(units)
    if n == 0:
        return []
    if n == 1:
        return [(units[0],)]
    e = _unit(emb)
    idx = np.arange(n)
    d_pos = np.abs(idx[:, None] - idx[None, :]) / n
    d_cos = 1.0 - np.maximum(e @ e.T, 0.0)
    d = lam * d_pos + (1.0 - lam) * d_cos
    a, b = np.triu_indices(n, 1)
    vals = d[a, b]
    keep = vals <= threshold
    a, b, vals = a[keep], b[keep], vals[keep]
    order = np.lexsort((b, a, vals))  # distance, then pair index: deterministic
    parent = list(range(n))
    size = [ue - us for us, ue in units]

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for k in order:
        ra, rb = find(int(a[k])), find(int(b[k]))
        if ra != rb and size[ra] + size[rb] <= cap:
            ra, rb = min(ra, rb), max(ra, rb)
            parent[rb] = ra
            size[ra] += size[rb]
    members: dict[int, list[int]] = {}
    for i in range(n):
        members.setdefault(find(i), []).append(i)
    out: list[Chunk] = []
    for idxs in members.values():
        ivs: list[list[int]] = []
        for i in sorted(idxs):
            s, e_ = units[i]
            if ivs and ivs[-1][1] == s:
                ivs[-1][1] = e_
            else:
                ivs.append([s, e_])
        out.append(tuple((s, e_) for s, e_ in ivs))
    return sorted(out, key=lambda c: c[0][0])


def chunk_text(doc: Document, chunk: Chunk) -> str:
    """Text of a chunk in document order; pieces of a non-contiguous chunk are joined by a newline."""
    return "\n".join(doc.words(s, e) for s, e in chunk)


def chunk_words(chunk: Chunk) -> int:
    return sum(e - s for s, e in chunk)
