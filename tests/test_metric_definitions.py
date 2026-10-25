"""Regression tests: the stored metrics are WORD-based; character-based variants differ.

The analysis plans define coverage over characters; the code converts gold character spans to word intervals
(`data.char_to_word_span`) and scores word overlap (`evaluate.span_metrics`). These tests pin both definitions so the
difference is explicit and cannot drift silently.
"""
import numpy as np
import pytest

from ragmv import charmetric as C
from ragmv import data as D
from ragmv import evaluate as E
from ragmv import evaluate_multi as EM


def _all(doc, retrieved_words, gold_chars):
    gold_words = D._dedupe([D.char_to_word_span(doc, s, e) for s, e in gold_chars])
    return C.all_variants(doc, retrieved_words, gold_words, gold_chars, C.nonspace_prefix(doc.text))


def test_unequal_word_lengths_distinguish_word_from_character_coverage():
    doc = D.make_document("d", "a bbbbbbbbb")
    res = _all(doc, [(0, 1)], [(0, 11)])  # retrieve only "a"; gold is the whole string
    assert res["word"][2] == pytest.approx(1 / 2)  # 1 of 2 words
    assert res["char"][2] == pytest.approx(1 / 11)  # 1 of 11 characters
    assert res["char_nows"][2] == pytest.approx(1 / 10)  # 1 of 10 non-space characters
    assert res["word"][1] == 1.0 and res["char"][1] == 0.0  # lenient hit differs too


def test_partial_word_gold_boundaries_expand_to_whole_words_only_in_the_word_metric():
    doc = D.make_document("d", "alpha beta gamma")
    gold = [(2, 8)]  # "pha be": starts and ends inside words
    assert D.char_to_word_span(doc, 2, 8) == (0, 2)
    res = _all(doc, [(0, 1)], gold)  # retrieve "alpha"
    assert res["word"][2] == pytest.approx(0.5)
    assert res["char"][2] == pytest.approx(3 / 6)  # "pha" of "pha be"
    assert res["char_nows"][2] == pytest.approx(3 / 5)
    full = _all(doc, [(0, 2)], gold)
    assert full["word"][0] == full["char"][0] == full["char_nows"][0] == 1.0


def test_whitespace_between_separately_retrieved_chunks():
    doc = D.make_document("d", "gamma.\n\nDelta")
    gold = [(0, 13)]
    res = _all(doc, [(0, 1), (1, 2)], gold)  # two adjacent one-word chunks
    assert res["word"] == (1.0, 1.0, 1.0)  # word intervals merge
    assert res["char"][0] == 0.0 and res["char"][2] == pytest.approx(11 / 13)  # "\n\n" is in no chunk's text
    assert res["char_nows"] == (1.0, 1.0, 1.0)
    assert D.char_to_word_span(doc, 6, 8) is None  # a gold span of whitespace only is dropped by the loaders


def test_overlapping_retrieved_intervals_are_not_double_counted():
    doc = D.make_document("d", "w0 w1 w2 w3 w4 w5 w6 w7 w8 w9")
    gold_chars = [(0, len(doc.text))]
    res = _all(doc, [(0, 4), (2, 6)], gold_chars)
    assert res["word"][2] == pytest.approx(6 / 10)
    assert res["char"][2] == pytest.approx(len("w0 w1 w2 w3 w4 w5") / len(doc.text))


def test_multiple_gold_spans_take_the_best_covered_span():
    doc = D.make_document("d", "aa bb cccccccccc dd")
    gold = [(0, 5), (6, 19)]  # "aa bb" and "cccccccccc dd"
    res = _all(doc, [(0, 1), (2, 3)], gold)  # "aa" and "cccccccccc"
    assert res["word"][2] == pytest.approx(0.5)  # both spans half covered in words
    assert res["char"][2] == pytest.approx(10 / 13)  # the long word dominates in characters
    assert res["word"][1] == 1.0 and res["char"][0] == 0.0


def test_non_contiguous_chunk_selection_scores_each_interval():
    doc = D.make_document("d", "x1 x2 x3 x4 x5 x6")
    chunk_ivs = [((0, 1), (3, 4))]  # one clustering chunk made of two separate words
    iv, used = EM.select_count([0], np.array([0]), chunk_ivs, 0, 1)
    assert iv == [(0, 1), (3, 4)] and used == 2
    res = _all(doc, iv, [(0, 8)])  # gold "x1 x2 x3"
    assert res["word"][2] == pytest.approx(1 / 3)
    assert res["char"][2] == pytest.approx(2 / 8)


def test_word_variant_equals_the_stored_metric_and_budget_truncation():
    doc = D.make_document("d", " ".join(f"t{i}" for i in range(40)))
    q = D.Query("q", 0, "?", [(5, 15)], [], [(int(doc.word_starts[5]), int(doc.word_ends[14]))])
    ranked = np.array([[1, 0]])
    cd, ws, we = np.array([0, 0]), np.array([0, 10]), np.array([10, 20])
    stored = E.evaluate_rankings(ranked, cd, ws, we, [q], (1, 2), (5, 15))
    new = C.evaluate_rankings_variants(ranked, cd, ws, we, [q], [doc], (1, 2), (5, 15))
    assert np.array_equal(stored["scores"], new["word_f16"]) and np.array_equal(stored["words"], new["words"])
    assert np.allclose(new["word"], stored["scores"].astype(np.float64), atol=1e-3)


def test_loaders_keep_character_spans_alongside_word_spans():
    contexts = [("doc", [("Alpha beta, gamma.", [{"id": "1", "question": "?", "answers": [{"text": "eta, g",
                                                                                           "answer_start": 7}]}])])]
    docs, queries = D._squad_like(contexts, "t:")
    q = queries[0]
    assert q.gold == [(1, 3)]  # "beta," and "gamma." overlap the partial-word answer
    assert q.gold_chars == [(7, 13)] and docs[0].text[7:13] == "eta, g"
