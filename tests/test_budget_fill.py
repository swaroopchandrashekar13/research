"""Budget-matched selection is filled whenever the corpus holds enough text (ragmv.budgetfill)."""
import math

import numpy as np
import pytest

from ragmv import evaluate as E
from ragmv import evaluate_multi as EM
from ragmv.budgetfill import RankingConsistencyError, fill_to_budget
from ragmv.dense import dense_rank, dense_rank_filled
from ragmv.retrieval import Ranker, RetrieverSpec, rank, rank_filled, tokenize
from ragmv.run import BUDGETS, KS

PLAIN = RetrieverSpec("lucene", 1.5, 0.75, False)


class Q:
    def __init__(self, doc_idx, gold):
        self.doc_idx, self.gold = doc_idx, gold


def _heuristic_depth(lengths):
    return min(len(lengths), max(KS) + math.ceil(max(BUDGETS) / max(1.0, float(np.percentile(lengths, 10)))) + 10)


def _adversarial_corpus():
    """90 one-word chunks that match the query best, then 910 chunks of 512 words that match it weakly."""
    short = ["apple"] * 90
    long_ = [" ".join(["apple"] + [f"w{i}x{j}" for j in range(511)]) for i in range(910)]
    texts = short + long_
    lengths = np.array([1] * 90 + [512] * 910)
    return texts, lengths


def _sorted_retriever(order, scores):
    """A retriever over a fixed full ranking (order, scores), best first."""
    order, scores = np.asarray(order), np.asarray(scores, dtype=np.float64)
    return (lambda i, d: (order[:d], scores[:d])), order, scores


def test_adversarial_short_chunks_first_is_filled():
    texts, lengths = _adversarial_corpus()
    depth = _heuristic_depth(lengths)
    assert float(np.percentile(lengths, 10)) == 512 and depth == 24
    ctok, qtok = tokenize(texts, False), tokenize(["apple"], False)
    old = rank(ctok, qtok, PLAIN, depth)
    assert set(old[0].tolist()) <= set(range(90))  # the short chunks rank first
    doc = np.zeros(len(texts), np.int64)
    ws = np.concatenate([[0], np.cumsum(lengths)[:-1]])
    _, words_old = E.select_budget(old[0], doc, ws, ws + lengths, 0, 2048)
    assert words_old == 24  # the defect: 24 words for a 2,048-word budget
    fill = rank_filled(ctok, qtok, PLAIN, depth, lengths, 2048)
    _, words_new = E.select_budget(fill.rows[0], doc, ws, ws + lengths, 0, 2048)
    assert words_new == 2048 and not fill.exhausted[0] and fill.expansions[0] >= 1
    assert fill.rows[0][:depth].tolist() == old[0].tolist()  # the original prefix is kept
    assert len(set(fill.rows[0].tolist())) == len(fill.rows[0])  # no chunk twice


def test_already_filled_queries_are_untouched():
    get, order, scores = _sorted_retriever(np.arange(50), np.linspace(1, 0, 50))
    fill = fill_to_budget(order[None, :10], scores[None, :10], np.full(50, 300), 2048, 50, get)
    assert fill.rows[0].tolist() == list(range(10)) and fill.expansions[0] == 0 and not fill.exhausted[0]


def test_corpus_exhaustion_stops_cleanly():
    get, order, scores = _sorted_retriever(np.arange(12), np.linspace(1, 0, 12))
    fill = fill_to_budget(order[None, :4], scores[None, :4], np.full(12, 10), 2048, 12, get)
    assert fill.exhausted[0] and fill.depth[0] == 12 and sorted(fill.rows[0].tolist()) == list(range(12))


def test_ties_are_deterministic_and_never_duplicate():
    texts = ["same words here"] * 300
    ctok, qtok = tokenize(texts, False), tokenize(["words"], False)
    a = rank_filled(ctok, qtok, PLAIN, 5, np.full(300, 3), 600)
    b = rank_filled(ctok, qtok, PLAIN, 5, np.full(300, 3), 600)
    assert a.rows[0].tolist() == b.rows[0].tolist()
    assert len(set(a.rows[0].tolist())) == len(a.rows[0]) and 3 * len(a.rows[0]) >= 600
    assert a.rows[0][:5].tolist() == rank(ctok, qtok, PLAIN, 5)[0].tolist()


def test_overlapping_chunks_are_charged_every_time():
    # windows of 100 words with stride 50: each chunk overlaps its neighbour by half
    ws = np.arange(0, 2000, 50)
    we = ws + 100
    get, order, scores = _sorted_retriever(np.arange(len(ws)), np.linspace(1, 0, len(ws)))
    fill = fill_to_budget(order[None, :3], scores[None, :3], we - ws, 1024, len(ws), get)
    iv, used = E.select_budget(fill.rows[0], np.zeros(len(ws), np.int64), ws, we, 0, 1024)
    assert used == 1024 and len(fill.rows[0]) >= 11  # 10 full chunks plus a truncated one
    assert sum(e - s for s, e in iv) == 1024


def test_noncontiguous_chunks_keep_interval_order_and_truncation():
    ivs = [((0, 3), (10, 12)), ((20, 30),), ((3, 10), (40, 41))] * 40
    lengths = np.array([sum(e - s for s, e in c) for c in ivs])
    get, order, scores = _sorted_retriever(np.arange(len(ivs)), np.linspace(1, 0, len(ivs)))
    fill = fill_to_budget(order[None, :2], scores[None, :2], lengths, 250, len(ivs), get)
    iv, used = EM.select_budget(fill.rows[0], np.zeros(len(ivs), np.int64), ivs, 0, 250)
    assert used == 250
    direct, used_direct = EM.select_budget(np.arange(len(ivs)), np.zeros(len(ivs), np.int64), ivs, 0, 250)
    assert (iv, used) == (direct, used_direct)  # same selection as ranking the full corpus


@pytest.mark.parametrize("n_chunks, budget", [(0, 128), (5, 0)])
def test_degenerate_inputs(n_chunks, budget):
    get, order, scores = _sorted_retriever(np.arange(n_chunks), np.linspace(1, 0, n_chunks))
    fill = fill_to_budget(order[None, :2], scores[None, :2], np.full(n_chunks, 4), budget, n_chunks, get)
    assert fill.expansions[0] == 0 and fill.exhausted[0] == (budget > 0 and n_chunks * 4 < budget)
    empty = fill_to_budget(np.zeros((0, 0), np.int64), np.zeros((0, 0)), np.zeros(0), 128, 0, get)
    assert empty.rows == [] and empty.depth.shape == (0,)


def test_count_matched_and_filled_budget_results_are_unchanged():
    rng = np.random.default_rng(3)
    n = 400
    lengths = rng.integers(1, 200, n)
    lengths[:30] = 1  # some queries rank short chunks first
    ws = np.concatenate([[0], np.cumsum(lengths)[:-1]])
    we = ws + lengths
    doc = rng.integers(0, 5, n)
    queries = [Q(int(rng.integers(0, 5)), [(int(ws[k]), int(we[k]))]) for k in rng.integers(0, n, 25)]
    full = [np.argsort(-rng.random(n), kind="stable") for _ in queries]
    full[0] = np.concatenate([np.arange(30), np.arange(30, n)])  # adversarial query
    sc = [np.linspace(1, 0, n) for _ in queries]
    depth = 24
    old = np.stack([f[:depth] for f in full])
    fill = fill_to_budget(old, np.stack([s[:depth] for s in sc]), lengths, max(BUDGETS), n,
                          lambda i, d: (full[i][:d], sc[i][:d]))
    a = E.evaluate_rankings(old, doc, ws, we, queries, KS, BUDGETS)
    b = E.evaluate_rankings(fill.rows, doc, ws, we, queries, KS, BUDGETS)
    nk = len(KS)
    assert np.array_equal(a["scores"][:, :nk], b["scores"][:, :nk]) and np.array_equal(a["rr10"], b["rr10"])
    for j, budget in enumerate(BUDGETS, nk):
        filled = a["words"][:, j] == budget
        assert np.array_equal(a["scores"][filled, j], b["scores"][filled, j])
        assert (b["words"][:, j] == budget).all()  # every query now reaches every budget
    assert not (a["words"][:, -1] == max(BUDGETS)).all()  # the old fixed depth did underfill


def test_dense_filled_extends_the_dense_ranking():
    rng = np.random.default_rng(0)
    c = rng.normal(size=(300, 8)).astype(np.float32)
    q = rng.normal(size=(6, 8)).astype(np.float32)
    lengths = np.full(300, 5)
    fill = dense_rank_filled(c, q, 4, lengths, 100)
    full = dense_rank(c, q, 300)
    for i in range(6):
        assert fill.rows[i].tolist() == full[i][: len(fill.rows[i])].tolist() and 5 * len(fill.rows[i]) >= 100


def test_bm25_ranker_matches_rank():
    texts = [f"term{i % 7} filler{i}" for i in range(80)]
    ctok, qtok = tokenize(texts, True), tokenize(["term3", "filler9 term1"], True)
    assert np.array_equal(Ranker(ctok, PLAIN).retrieve(qtok, 10)[0], rank(ctok, qtok, PLAIN, 10))


def test_inconsistent_expansion_is_an_error():
    order = np.arange(20)
    scores = np.linspace(1, 0, 20)

    def bad(i, d):  # a deeper ranking that puts a new chunk above the old prefix
        o = np.concatenate([[19], order[:-1]])[:d]
        return o, np.concatenate([[2.0], scores[:-1]])[:d]
    with pytest.raises(RankingConsistencyError):
        fill_to_budget(order[None, :3], scores[None, :3], np.ones(20), 10, 20, bad)


def test_short_expansion_cannot_loop_forever():
    with pytest.raises(RankingConsistencyError, match="asked for"):
        fill_to_budget(np.arange(3)[None], np.ones((1, 3)), np.ones(50), 40, 50, lambda i, d: (np.arange(3), np.ones(3)))


def test_repeated_execution_is_stable():
    texts, lengths = _adversarial_corpus()
    ctok, qtok = tokenize(texts, False), tokenize(["apple", "w3x5"], False)
    a = rank_filled(ctok, qtok, PLAIN, 24, lengths, 2048)
    b = rank_filled(ctok, qtok, PLAIN, 24, lengths, 2048)
    assert all(np.array_equal(x, y) for x, y in zip(a.rows, b.rows)) and np.array_equal(a.depth, b.depth)
