import os
from pathlib import Path

import numpy as np
import pytest

from ragmv import data as D
from ragmv.chunking import ChunkSpec, chunk_document, default_specs, fixed_windows, paragraph_bounds, sentence_bounds
from ragmv.evaluate import evaluate_rankings, merge, rr_at, select_budget, select_count, span_metrics
from ragmv.retrieval import RetrieverSpec, default_retrievers, rank, tokenize
from ragmv import stats as S

RAW = Path(os.environ.get("RAGMV_DATA_ROOT") or Path(__file__).resolve().parents[1] / "data" / "raw")


# ----------------------------------------------------------------------------- documents and spans
def test_word_offsets_paragraphs_and_char_to_word():
    doc = D.make_document("d", "Alpha beta, gamma.\n\nDelta epsilon")
    assert [doc.words(i, i + 1) for i in range(doc.n_words)] == ["Alpha", "beta,", "gamma.", "Delta", "epsilon"]
    assert doc.para_of_word.tolist() == [0, 0, 0, 1, 1]
    assert D.char_to_word_span(doc, 6, 10) == (1, 2)  # "beta"
    assert D.char_to_word_span(doc, 12, 25) == (2, 4)  # "gamma.\n\nDelta"
    assert D.char_to_word_span(doc, 8, 15) == (1, 3)  # partial words on both ends
    assert D.char_to_word_span(doc, 18, 20) is None  # whitespace only


def test_split_is_deterministic_and_sized():
    a, b = D.split_documents(100), D.split_documents(100)
    assert (a == b).all() and a.sum() == 20
    assert not (D.split_documents(100, seed=1) == a).all()


# ----------------------------------------------------------------------------- chunking
def test_fixed_windows_with_and_without_overlap():
    assert fixed_windows(0, 10, 4) == [(0, 4), (4, 8), (8, 10)]
    assert fixed_windows(0, 10, 4, 0.25) == [(0, 4), (3, 7), (6, 10)]
    assert fixed_windows(0, 4, 4, 0.25) == [(0, 4)]


def test_sentence_splitter_respects_abbreviations():
    doc = D.make_document("d", "This is one. This is two! See e.g. the rest. Third part")
    sents = [doc.words(s, e) for s, e in sentence_bounds(doc, 0, doc.n_words)]
    assert sents == ["This is one.", "This is two!", "See e.g. the rest.", "Third part"]


def _synthetic_doc(rng):
    paras = []
    for _ in range(12):
        sents = [" ".join(f"w{rng.integers(1000)}" for _ in range(rng.integers(3, 40))) + "." for _ in range(rng.integers(1, 6))]
        paras.append(" ".join(s[0].upper() + s[1:] for s in sents))
    return D.make_document("syn", "\n\n".join(paras))


@pytest.mark.parametrize("spec", [s for s in default_specs() if s.overlap == 0], ids=lambda s: s.name)
def test_non_overlapping_chunkers_partition_words_within_size(spec):
    doc = _synthetic_doc(np.random.default_rng(0))
    chunks = chunk_document(doc, spec)
    assert chunks[0][0] == 0 and chunks[-1][1] == doc.n_words
    assert all(a[1] == b[0] for a, b in zip(chunks, chunks[1:])), "gap or overlap between chunks"
    assert all(0 < e - s <= spec.size for s, e in chunks)


def test_paragraph_chunks_never_cross_paragraphs_unless_packing_whole_ones():
    doc = _synthetic_doc(np.random.default_rng(1))
    starts = {s for s, _ in paragraph_bounds(doc)}
    for s, e in chunk_document(doc, ChunkSpec("paragraph", 64)):
        paras = set(doc.para_of_word[s:e].tolist())
        if len(paras) > 1:  # a packed chunk must start at a paragraph start and contain only whole paragraphs
            assert s in starts and (e == doc.n_words or e in starts)


def test_overlapping_chunker_stride():
    doc = _synthetic_doc(np.random.default_rng(2))
    chunks = chunk_document(doc, ChunkSpec("fixed", 128, 0.25))
    assert all(b[0] - a[0] == 96 for a, b in zip(chunks, chunks[1:]))
    assert chunks[-1][1] == doc.n_words


# ----------------------------------------------------------------------------- metrics and protocols
def test_merge_and_span_metrics_hand_computed():
    assert merge([(5, 8), (0, 3), (3, 5), (10, 12)]) == [(0, 8), (10, 12)]
    gold = [(10, 20)]
    assert span_metrics([(0, 15), (15, 30)], gold) == (1.0, 1.0, 1.0)  # union covers the span
    assert span_metrics([(0, 15)], gold) == (0.0, 1.0, 0.5)  # exactly 50% -> lenient hit
    assert span_metrics([(0, 14)], gold) == (0.0, 0.0, 0.4)
    assert span_metrics([], gold) == (0.0, 0.0, 0.0)
    assert span_metrics([(0, 12), (18, 40)], [(10, 20), (30, 35)]) == (1.0, 1.0, 1.0)  # second span fully covered


CH_DOC = np.array([0, 0, 1, 0])
CH_WS = np.array([0, 40, 0, 100])
CH_WE = np.array([50, 90, 60, 150])


def test_count_selection_counts_all_documents_words():
    iv, words = select_count([2, 0, 1], CH_DOC, CH_WS, CH_WE, gold_doc=0, k=2)
    assert iv == [(0, 50)] and words == 110


def test_budget_selection_is_exact_and_truncates_last_chunk():
    iv, used = select_budget([2, 0, 1, 3], CH_DOC, CH_WS, CH_WE, gold_doc=0, budget=130)
    # chunk 2 (other doc, 60 words) consumes budget; chunk 0 (50) fits; chunk 1 truncated to 20 words
    assert used == 130 and iv == [(0, 50), (40, 60)]
    iv, used = select_budget([0], CH_DOC, CH_WS, CH_WE, gold_doc=0, budget=500)
    assert used == 50 and iv == [(0, 50)]  # ranking exhausted before budget


def test_overlapping_text_counts_against_budget():
    iv, used = select_budget([0, 1], CH_DOC, CH_WS, CH_WE, gold_doc=0, budget=100)
    assert used == 100 and iv == [(0, 50), (40, 90)]
    assert span_metrics(iv, [(0, 90)])[2] == 1.0


def test_rr_requires_single_chunk_containment():
    assert rr_at([2, 1, 0], CH_DOC, CH_WS, CH_WE, 0, [(45, 55)]) == 0.5
    assert rr_at([0, 1], CH_DOC, CH_WS, CH_WE, 0, [(45, 95)]) == 0.0


def test_evaluate_rankings_shapes_and_values():
    q = D.Query("q", 0, "?", [(40, 60)], [])
    res = evaluate_rankings(np.array([[1, 0, 2, 3]]), CH_DOC, CH_WS, CH_WE, [q], ks=(1, 2), budgets=(10, 100))
    assert res["scores"].shape == (1, 4, 3)
    assert res["scores"][0, 0].tolist() == [1.0, 1.0, 1.0]  # k=1: chunk 1 = (40, 90) contains span
    assert res["scores"][0, 2].tolist() == [0.0, 1.0, 0.5]  # B=10: (40, 50) = exactly half -> lenient hit
    assert res["words"][0].tolist() == [50, 100, 10, 100]


# ----------------------------------------------------------------------------- retrieval
def test_bm25_ranks_matching_chunk_first_and_handles_empty_query():
    texts = ["the cat sat on the mat", "a dog ran fast", "cats and dogs"]
    for stem in (True, False):
        ranked = rank(tokenize(texts, stem), tokenize(["cat mat", "the of and"], stem), RetrieverSpec("lucene", 1.5, 0.75, stem), 3)
        assert ranked.shape == (2, 3) and ranked[0, 0] == 0


def test_sixteen_planned_retrievers_and_chunkings():
    assert len(default_retrievers()) == 16 and len({r.name for r in default_retrievers()}) == 16
    assert len(default_specs()) == 16 and len({s.name for s in default_specs()}) == 16


# ----------------------------------------------------------------------------- statistics
def test_bootstrap_ci_and_verdicts():
    rng = np.random.default_rng(3)
    diff = np.column_stack([rng.normal(0.3, 1, 400), rng.normal(0.0, 1, 400), rng.normal(-0.3, 1, 400)])
    mean, lo, hi, p = S.paired_bootstrap_ci(diff, reps=1000, seed=1)
    assert (lo < mean).all() and (mean < hi).all()
    assert S.verdicts(lo, hi).tolist() == [1, 0, -1]
    assert p[0] < 0.05 and p[1] > 0.05 and p[2] < 0.05


def test_cluster_bootstrap_weights_follow_clusters():
    clusters = np.array([0, 0, 1, 2, 2, 2])
    w = S.bootstrap_weights(6, 200, seed=2, clusters=clusters)
    assert (w[:, 0] == w[:, 1]).all() and (w[:, 3] == w[:, 5]).all()
    assert set(np.unique(w.sum(axis=1) % 1)) == {0.0}


def test_cluster_bootstrap_is_wider_when_effects_cluster():
    rng = np.random.default_rng(6)
    clusters = np.repeat(np.arange(10), 50)
    diff = (rng.normal(0, 1, 10)[clusters] + rng.normal(0, 0.2, 500))[:, None]
    _, lo_q, hi_q, _ = S.paired_bootstrap_ci(diff, reps=1000, seed=3)
    _, lo_c, hi_c, _ = S.paired_bootstrap_ci(diff, reps=1000, seed=3, clusters=clusters)
    assert (hi_c - lo_c)[0] > 2 * (hi_q - lo_q)[0]


def test_benjamini_hochberg():
    assert S.bh_reject(np.array([0.001, 0.02, 0.03, 0.5])).tolist() == [True, True, True, False]
    assert S.bh_reject(np.array([0.2, 0.3])).tolist() == [False, False]


def test_required_n_formula():
    assert S.required_n(np.array([0.1]))[0] == 197  # ((1.96+0.8416)*0.1/0.02)^2 = 196.2


def test_eta_squared_matches_statsmodels_on_balanced_design():
    import pandas as pd
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    rng = np.random.default_rng(4)
    a, b = np.repeat(np.arange(4), 30), np.tile(np.repeat(np.arange(3), 10), 4)
    y = a * 0.5 + b * 0.1 + rng.normal(0, 0.2, len(a))
    ours = S.eta_squared(y, {"a": a, "b": b})
    table = sm.stats.anova_lm(smf.ols("y ~ C(a) + C(b)", pd.DataFrame({"y": y, "a": a, "b": b})).fit(), typ=2)
    total = ((y - y.mean()) ** 2).sum()
    assert ours["a"] == pytest.approx(table.loc["C(a)", "sum_sq"] / total, rel=1e-9)
    assert ours["b"] == pytest.approx(table.loc["C(b)", "sum_sq"] / total, rel=1e-9)


def test_joint_bootstrap_shares_runs_and_is_bounded():
    rng = np.random.default_rng(5)
    diffs = {"x": rng.normal(0.2, 1, (300, 6)), "y": rng.normal(0, 1, (200, 4))}
    reps = S.joint_bootstrap_shares(diffs, lambda v: float(np.mean(np.concatenate(list(v.values())) == 1)), reps=50)
    assert reps.shape == (50,) and (0 <= reps).all() and (reps <= 1).all()


# ----------------------------------------------------------------------------- real data (skipped if absent)
def _norm(s):
    return " ".join(s.split())


@pytest.mark.parametrize("name", ["squad2", "covidqa", "cuad"])
def test_gold_spans_contain_answer_text(name):
    if not (RAW / name).exists():
        pytest.skip("raw data not downloaded")
    docs, queries = D.load(name, RAW)
    for q in queries[:: max(1, len(queries) // 300)]:
        doc = docs[q.doc_idx]
        spans = [_norm(doc.words(s, e)) for s, e in q.gold]
        assert any(_norm(a) in sp for a in q.answers for sp in spans), (q.qid, q.answers[:2], spans[:2])


def test_qasper_gold_spans_are_whole_paragraphs():
    if not (RAW / "qasper" / "qasper-test-v0.3.json").exists():
        pytest.skip("raw data not downloaded")
    docs, queries = D.load("qasper", RAW)
    assert len(queries) > 500
    for q in queries[::50]:
        doc = docs[q.doc_idx]
        for s, e in q.gold:
            assert len(set(doc.para_of_word[s:e].tolist())) == 1
            assert s == 0 or doc.para_of_word[s - 1] != doc.para_of_word[s]


def test_joint_bootstrap_respects_clusters():
    # Effects that live at the document level: cluster resampling must give a wider replicate spread.
    rng = np.random.default_rng(8)
    clusters = np.repeat(np.arange(8), 60)
    d = (rng.normal(0, 1, 8)[clusters] + rng.normal(0, 0.1, 480))[:, None]
    mean_of = lambda st: float(st["x"][0][0])
    q = S.joint_bootstrap({"x": d}, mean_of, reps=300, seed=1)
    c = S.joint_bootstrap({"x": d}, mean_of, reps=300, seed=1, clusters={"x": clusters})
    assert c.std() > 3 * q.std()
