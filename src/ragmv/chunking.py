"""Offset-exact chunkers. A chunk is a half-open word interval (ws, we) within one document."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .data import Document

_SENT_END = re.compile(r"[.!?][\"'”’)\]]*$")
_ABBREV = {
    "e.g.", "i.e.", "et", "al.", "fig.", "figs.", "eq.", "eqs.", "no.", "vs.", "dr.", "mr.", "mrs.", "ms.",
    "inc.", "ltd.", "co.", "corp.", "sec.", "art.", "u.s.", "st.", "jr.", "sr.", "approx.", "ref.", "refs.",
}


@dataclass(frozen=True)
class ChunkSpec:
    family: str  # fixed | sentence | paragraph
    size: int  # W, maximum words per chunk
    overlap: float = 0.0  # fraction of W, fixed family only

    @property
    def name(self) -> str:
        return f"{self.family}-{self.size}" + (f"-o{int(self.overlap * 100)}" if self.overlap else "")


def fixed_windows(ws: int, we: int, size: int, overlap: float = 0.0) -> list[tuple[int, int]]:
    stride = size - round(overlap * size)
    if stride <= 0:
        raise ValueError("overlap must be < 1")
    out, s = [], ws
    while s < we:
        e = min(s + size, we)
        out.append((s, e))
        if e == we:
            break
        s += stride
    return out


def sentence_bounds(doc: Document, ws: int, we: int) -> list[tuple[int, int]]:
    """Split words [ws, we) into sentences with a rule-based splitter (punctuation + next-word capital/digit)."""
    out, start = [], ws
    for i in range(ws, we - 1):
        w = doc.text[doc.word_starts[i]: doc.word_ends[i]]
        if not _SENT_END.search(w) or w.lower() in _ABBREV:
            continue
        nxt = doc.text[doc.word_starts[i + 1]]
        if nxt.isupper() or nxt.isdigit() or nxt in "\"'(“[":
            out.append((start, i + 1))
            start = i + 1
    if start < we:
        out.append((start, we))
    return out


def _pack(units: list[tuple[int, int]], size: int, split_long) -> list[tuple[int, int]]:
    """Greedily pack consecutive units into chunks of at most `size` words; long units are split by `split_long`."""
    out, cur = [], None
    for us, ue in units:
        n = ue - us
        if n > size:
            if cur:
                out.append(cur)
                cur = None
            out.extend(split_long(us, ue))
        elif cur is None:
            cur = (us, ue)
        elif ue - cur[0] <= size:
            cur = (cur[0], ue)
        else:
            out.append(cur)
            cur = (us, ue)
    if cur:
        out.append(cur)
    return out


def paragraph_bounds(doc: Document) -> list[tuple[int, int]]:
    out, start = [], 0
    for i in range(1, doc.n_words):
        if doc.para_of_word[i] != doc.para_of_word[i - 1]:
            out.append((start, i))
            start = i
    if doc.n_words:
        out.append((start, doc.n_words))
    return out


def chunk_document(doc: Document, spec: ChunkSpec) -> list[tuple[int, int]]:
    n, w = doc.n_words, spec.size
    if n == 0:
        return []
    if spec.family == "fixed":
        return fixed_windows(0, n, w, spec.overlap)

    def by_sentence(s: int, e: int) -> list[tuple[int, int]]:
        return _pack(sentence_bounds(doc, s, e), w, lambda a, b: fixed_windows(a, b, w))

    if spec.family == "sentence":
        return by_sentence(0, n)
    if spec.family == "paragraph":
        return _pack(paragraph_bounds(doc), w, by_sentence)
    raise ValueError(f"unknown chunk family {spec.family!r}")


def default_specs() -> list[ChunkSpec]:
    """The 16 planned chunkings (analysis plan §2.1)."""
    sizes = (64, 128, 256, 512)
    return (
        [ChunkSpec("fixed", s) for s in sizes]
        + [ChunkSpec("fixed", s, 0.25) for s in sizes]
        + [ChunkSpec("sentence", s) for s in sizes]
        + [ChunkSpec("paragraph", s) for s in sizes]
    )
