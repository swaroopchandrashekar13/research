import json
import os
import zlib
from pathlib import Path

import numpy as np
import pytest

from ragmv import evaluate as E
from ragmv import evaluate_multi as EM
from ragmv import run1b
from ragmv.dense import dense_rank
from ragmv.semantic import breakpoint_chunks, chunk_words, clustering_chunks

RAW = Path(os.environ.get("RAGMV_DATA_ROOT") or Path(__file__).resolve().parents[1] / "data" / "raw")
E1 = Path(__file__).resolve().parents[1] / "experiments" / "E1_retrieval_multiverse" / "runs" / "confirmatory-20261018"


class FakeQuery:
    def __init__(self, doc_idx, gold):
        self.doc_idx, self.gold = doc_idx, gold


def test_multi_interval_evaluation_equals_study1_for_contiguous_chunks():
    rng = np.random.default_rng(0)
    n = 60
    chunk_doc = rng.integers(0, 3, n)
    ws = rng.integers(0, 500, n)
    we = ws + rng.integers(1, 120, n)
    ivs = [((int(a), int(b)),) for a, b in zip(ws, we)]
    queries = [FakeQuery(int(rng.integers(0, 3)), [(int(s), int(s) + int(rng.integers(1, 30)))])
               for s in rng.integers(0, 550, 25)]
    ranked = np.stack([rng.permutation(n) for _ in queries])
    a = E.evaluate_rankings(ranked, chunk_doc, ws, we, queries, (1, 3, 5, 10), (128, 256, 512, 1024, 2048))
    b = EM.evaluate_rankings(ranked, chunk_doc, ivs, queries, (1, 3, 5, 10), (128, 256, 512, 1024, 2048))
    for k in a:
        assert np.array_equal(a[k], b[k]), k


def test_budget_truncates_noncontiguous_chunk_in_document_order():
    ivs = [((0, 10), (50, 60))]
    out, used = EM.select_budget([0], np.array([0]), ivs, 0, 15)
    assert out == [(0, 10), (50, 55)] and used == 15
    out, used = EM.select_count([0], np.array([0]), ivs, 0, 1)
    assert out == [(0, 10), (50, 60)] and used == 20


def _topic_emb(topics, dim=8):
    base = np.eye(dim)
    return np.stack([base[t] + 0.01 * i for i, t in enumerate(topics)])


def test_breakpoint_splits_at_topic_change_and_covers_document():
    units = [(i * 10, i * 10 + 10) for i in range(20)]
    topics = [0] * 10 + [1] * 10
    chunks = breakpoint_chunks(units, _topic_emb(topics))
    assert chunks[0] == ((0, 100),) and chunks[1] == ((100, 200),)
    covered = sorted(iv for c in chunks for iv in c)
    assert covered[0][0] == 0 and covered[-1][1] == 200 and all(len(c) == 1 for c in chunks)
    assert all(chunk_words(c) <= 512 for c in breakpoint_chunks([(i * 100, i * 100 + 100) for i in range(12)],
                                                               _topic_emb([0] * 12)))


def test_clustering_is_a_capped_partition_and_can_be_noncontiguous():
    units = [(i * 10, i * 10 + 10) for i in range(12)]
    topics = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]  # alternating topics -> clusters skip sentences
    chunks = clustering_chunks(units, _topic_emb(topics), cap=60, lam=0.1)
    words = sorted((s, e) for c in chunks for iv in c for s, e in [iv])
    flat = []
    for s, e in words:
        flat.extend(range(s, e))
    assert flat == list(range(120))  # every word exactly once
    assert all(chunk_words(c) <= 60 for c in chunks)
    assert any(len(c) > 1 for c in chunks)
    assert chunks == clustering_chunks(units, _topic_emb(topics), cap=60, lam=0.1)  # deterministic


def test_clustering_threshold_stops_merging():
    units = [(i * 10, i * 10 + 10) for i in range(4)]
    chunks = clustering_chunks(units, np.eye(4), threshold=0.1)  # all pairs orthogonal: nothing merges
    assert chunks == [((0, 10),), ((10, 20),), ((20, 30),), ((30, 40),)]


def test_dense_rank_orders_by_similarity_with_stable_ties():
    c = np.array([[1, 0], [0, 1], [1, 0], [0.6, 0.8]], dtype=np.float32)
    q = np.array([[1, 0]], dtype=np.float32)
    assert dense_rank(c, q, 4).tolist() == [[0, 2, 3, 1]]


def test_bm25_fixed_reproduces_study1_confirmatory_scores(tmp_path):
    if not (RAW / "covidqa").exists() or not (E1 / "covidqa" / "fixed-128.npz").exists():
        pytest.skip("data or E1 run not present")
    run1b.main(["--dataset", "covidqa", "--split", "confirmatory", "--out", str(tmp_path), "--chunkings",
                "fixed-128", "fixed-512", "--retrievers", "bm25", "--max-queries", "40", "--data-root", str(RAW)])
    cfg = json.loads((E1 / "covidqa" / "manifest.json").read_text())["config"]
    r = cfg["retrievers"].index(run1b.BM25.name)
    for name in ("fixed-128", "fixed-512"):
        new = np.load(tmp_path / "covidqa" / f"{name}.npz", allow_pickle=False)
        old = np.load(E1 / "covidqa" / f"{name}.npz", allow_pickle=False)
        assert np.array_equal(new["scores"][0], old["scores"][r][:40])
        assert np.array_equal(new["words"][0], old["words"][r][:40])


class HashEncoder:
    """Deterministic bag-of-words hashing encoder: stands in for bge-m3 in tests."""
    name = "hash-encoder"

    def encode(self, texts):
        out = np.zeros((len(texts), 64), dtype=np.float32)
        for i, t in enumerate(texts):
            for w in t.lower().split():
                out[i, zlib.crc32(w.encode()) % 64] += 1.0
        n = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(n == 0, 1, n)


def test_run1b_end_to_end_with_fake_encoder(tmp_path, monkeypatch):
    if not (RAW / "covidqa").exists():
        pytest.skip("raw data not downloaded")
    assert run1b.main(["--dataset", "covidqa", "--split", "exploratory", "--out", str(tmp_path / "run"),
                       "--max-queries", "15", "--cache-dir", str(tmp_path / "cache"), "--data-root", str(RAW)],
                      encoder=HashEncoder()) == 0
    m = json.loads((tmp_path / "run" / "covidqa" / "manifest.json").read_text())
    assert [s["chunking"] for s in m["chunk_stats"]] == list(run1b.CHUNKINGS) and m["encoder"] == "hash-encoder"
    for name in run1b.CHUNKINGS:
        z = np.load(tmp_path / "run" / "covidqa" / f"{name}.npz", allow_pickle=False)
        assert z["scores"].shape == (2, 15, 9, 3)
    stats = {s["chunking"]: s for s in m["chunk_stats"]}
    assert stats["semantic-cl"]["chunk_words_max"] <= 512 and stats["semantic-bp"]["chunk_words_max"] <= 512


def _synthetic_run(root: Path, n=60, seed=0):
    from ragmv.run import OPS

    rng = np.random.default_rng(seed)
    lengths = {"fixed-128": 128, "fixed-256": 256, "fixed-512": 512, "semantic-bp": 200, "semantic-cl": 300}
    d = root / "squad2"
    d.mkdir(parents=True)
    (d / "queries.json").write_text(json.dumps({"qids": list(range(n)), "doc_idx": list(range(n))}))
    (d / "manifest.json").write_text(json.dumps({
        "status": "ok", "error": None, "config": {"retrievers": ["bm25", "dense"], "ops": OPS},
        "chunk_stats": [{"chunking": k, "chunk_words_mean": v} for k, v in lengths.items()]}))
    for name, w in lengths.items():
        s = np.full((2, n, len(OPS), 3), 0.5, dtype=np.float32)
        s[:, :, :4, :] += 0.3 * (w / 512)  # count-matched: longer chunks win
        s[:, :, 4:, :] += 0.3 * (1 - w / 512)  # budget-matched: shorter chunks win
        s += rng.normal(0, 0.02, s.shape)
        np.savez_compressed(d / f"{name}.npz", scores=s.astype(np.float16))


def test_analysis_orients_on_the_shorter_arm(tmp_path):
    from ragmv import analyze1b
    from ragmv.analyze import Run

    _synthetic_run(tmp_path)
    res = analyze1b.analyze(Run(tmp_path), reps=300, joint_reps=100)
    assert res["shorter_arm"]["S5-128"]["squad2"] == "fixed-128" and res["shorter_arm"]["S5-256"]["squad2"] == "semantic-bp"
    assert res["H4"]["estimate"] > 0.9 and res["H4"]["verdict"] == "supported"
    assert res["H4b"]["verdict"] == "supported" and res["H5"]["verdict"] == "supported"
    assert res["H5b"]["verdict"] == "supported" and res["H5b"]["estimate"] > 0.9  # shorter arm = fixed-128
    assert "f_dense_only" in res["H4_sensitivity"]
    assert "H4" in analyze1b.to_markdown(res, "SMOKE")
