"""Dataset loaders producing documents with word offsets and queries with gold spans in word indices.

All gold evidence is converted from character intervals to half-open word intervals [ws, we) over the
document's `\\S+` words: every word that overlaps the character interval is included (a gold boundary inside a word
extends the span to the whole word; a span touching only whitespace is dropped). Study 1, Study 1b and the Tier 2
retrieval metrics are computed on these **word** intervals. The original character intervals are kept in
`Query.gold_chars` (same documents, same filtering) for the post-hoc character-based sensitivity analysis
(`ragmv.charmetric`); they are not used by the planned analyses.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

WORD_RE = re.compile(r"\S+")
PARA_BREAK_RE = re.compile(r"\n[ \t\r\f\v]*\n")


@dataclass
class Document:
    doc_id: str
    text: str
    word_starts: np.ndarray = field(repr=False)  # char offset of each word start
    word_ends: np.ndarray = field(repr=False)  # char offset one past each word end
    para_of_word: np.ndarray = field(repr=False)  # paragraph index of each word

    @property
    def n_words(self) -> int:
        return len(self.word_starts)

    def words(self, ws: int, we: int) -> str:
        if we <= ws:
            return ""
        return self.text[self.word_starts[ws]: self.word_ends[we - 1]]


@dataclass
class Query:
    qid: str
    doc_idx: int
    question: str
    gold: list[tuple[int, int]]  # word intervals in documents[doc_idx]
    answers: list[str]
    gold_chars: list[tuple[int, int]] = field(default_factory=list)  # source character intervals (same spans)


def make_document(doc_id: str, text: str) -> Document:
    spans = [(m.start(), m.end()) for m in WORD_RE.finditer(text)]
    starts = np.array([s for s, _ in spans], dtype=np.int64)
    ends = np.array([e for _, e in spans], dtype=np.int64)
    breaks = np.array([m.start() for m in PARA_BREAK_RE.finditer(text)], dtype=np.int64)
    para = np.searchsorted(breaks, starts, side="right") if len(starts) else np.zeros(0, dtype=np.int64)
    return Document(doc_id, text, starts, ends, para.astype(np.int64))


def char_to_word_span(doc: Document, cs: int, ce: int) -> tuple[int, int] | None:
    """Words overlapping the char interval [cs, ce). None if the interval touches no word."""
    if ce <= cs:
        return None
    ws = int(np.searchsorted(doc.word_ends, cs, side="right"))  # first word ending after cs
    we = int(np.searchsorted(doc.word_starts, ce, side="left"))  # first word starting at/after ce
    return (ws, we) if we > ws else None


def _dedupe(spans):
    return sorted(set(s for s in spans if s is not None))


# ----------------------------------------------------------------------------- SQuAD-format loaders

def _squad_like(contexts_by_doc: list[tuple[str, list[tuple[str, list[dict]]]]], qid_prefix: str):
    """contexts_by_doc: [(doc_id, [(paragraph_text, qas), ...])]; paragraphs joined by a blank line."""
    docs, queries = [], []
    for doc_id, paragraphs in contexts_by_doc:
        parts, offsets, pos = [], [], 0
        for ptext, _ in paragraphs:
            offsets.append(pos)
            parts.append(ptext)
            pos += len(ptext) + 2
        doc = make_document(doc_id, "\n\n".join(parts))
        d_idx = len(docs)
        docs.append(doc)
        for (ptext, qas), off in zip(paragraphs, offsets):
            for qa in qas:
                if qa.get("is_impossible") or not qa.get("answers"):
                    continue
                gold, answers, chars = [], [], []
                for a in qa["answers"]:
                    cs = off + a["answer_start"]
                    span = char_to_word_span(doc, cs, cs + len(a["text"]))
                    gold.append(span)
                    if span is not None:
                        chars.append((cs, cs + len(a["text"])))
                    answers.append(a["text"])
                gold = _dedupe(gold)
                if gold:
                    queries.append(Query(f"{qid_prefix}{qa['id']}", d_idx, qa["question"], gold, sorted(set(answers)),
                                         _dedupe(chars)))
    return docs, queries


def load_squad2(root: Path):
    data = json.loads((root / "squad2" / "dev-v2.0.json").read_text())["data"]
    return _squad_like([(a["title"], [(p["context"], p["qas"]) for p in a["paragraphs"]]) for a in data], "squad2:")


def load_covidqa(root: Path):
    data = json.loads((root / "covidqa" / "COVID-QA.json").read_text())["data"]
    items = [(str(d["paragraphs"][0]["document_id"]), [(p["context"], p["qas"]) for p in d["paragraphs"]]) for d in data]
    return _squad_like(items, "covidqa:")


def load_cuad(root: Path):
    data = json.loads((root / "cuad" / "test.json").read_text())["data"]
    return _squad_like([(d["title"], [(p["context"], p["qas"]) for p in d["paragraphs"]]) for d in data], "cuad:")


# ----------------------------------------------------------------------------- Qasper

def _norm_ws(s: str) -> str:
    return " ".join(s.split())


def load_qasper(root: Path, files=("qasper-dev-v0.3.json", "qasper-test-v0.3.json")):
    docs, queries = [], []
    for fname in files:
        papers = json.loads((root / "qasper" / fname).read_text())
        for pid, paper in papers.items():
            parts = []
            for sec in paper["full_text"]:
                if sec.get("section_name"):
                    parts.append(sec["section_name"])
                parts.extend(p for p in sec["paragraphs"] if p and p.strip())
            text = "\n\n".join(parts)
            doc = make_document(pid, text)
            d_idx = len(docs)
            docs.append(doc)
            # Locate evidence paragraphs by exact match after whitespace normalisation, at paragraph level.
            para_index = {}
            pos = 0
            for part in parts:
                para_index.setdefault(_norm_ws(part), (pos, pos + len(part)))
                pos += len(part) + 2
            for qa in paper["qas"]:
                gold, answers, chars = [], [], []
                for ann in qa["answers"]:
                    a = ann["answer"]
                    if a.get("unanswerable"):
                        continue
                    for ev in a.get("evidence", []):
                        if ev.startswith("FLOAT SELECTED"):
                            continue
                        hit = para_index.get(_norm_ws(ev))
                        if hit:
                            span = char_to_word_span(doc, *hit)
                            gold.append(span)
                            if span is not None:
                                chars.append(hit)
                    answers.extend(a.get("extractive_spans") or [])
                    if a.get("free_form_answer"):
                        answers.append(a["free_form_answer"])
                    if a.get("yes_no") is not None:
                        answers.append("yes" if a["yes_no"] else "no")
                gold = _dedupe(gold)
                if gold:
                    queries.append(Query(f"qasper:{qa['question_id']}", d_idx, qa["question"], gold, sorted(set(answers)),
                                         _dedupe(chars)))
    return docs, queries


LOADERS = {"squad2": load_squad2, "covidqa": load_covidqa, "cuad": load_cuad, "qasper": load_qasper}


def load(name: str, root: Path = Path("data/raw")):
    return LOADERS[name](root)


def split_documents(n_docs: int, frac_exploratory: float = 0.2, seed: int = 20261018) -> np.ndarray:
    """Boolean mask over documents: True = exploratory. Deterministic for a given (n_docs, seed)."""
    idx = list(range(n_docs))
    random.Random(seed).shuffle(idx)
    mask = np.zeros(n_docs, dtype=bool)
    mask[idx[: max(1, round(frac_exploratory * n_docs))]] = True
    return mask
