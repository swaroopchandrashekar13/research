"""Analysis sign conventions and indexing on a synthetic run whose correct answers are known by construction."""
import json

import numpy as np
import pytest

from ragmv import analyze as A
from ragmv.chunking import default_specs
from ragmv.run import BUDGETS, KS, OPS

N_Q, N_R, N_M = 300, 2, 3


def _write_run(tmp_path, effect):
    """effect(chunking, op_index) -> per-query mean score; noise is small so verdicts are unambiguous."""
    rng = np.random.default_rng(0)
    d = tmp_path / "squad2"
    d.mkdir(parents=True)
    retrievers = ["lucene-k1.5-b0.75-stem", "bm25+-k0.9-b0.4-plain"]
    (d / "queries.json").write_text(json.dumps({"qids": [str(i) for i in range(N_Q)], "doc_idx": [i // 10 for i in range(N_Q)]}))
    (d / "manifest.json").write_text(json.dumps({
        "status": "ok", "error": None, "git": "test", "config_sha256": "x", "started_utc": "t",
        "config": {"retrievers": retrievers, "ops": OPS}}))
    for spec in default_specs():
        scores = np.zeros((N_R, N_Q, len(OPS), N_M), dtype=np.float16)
        for o in range(len(OPS)):
            scores[:, :, o, :] = np.clip(effect(spec.name, o) + rng.normal(0, 0.01, (N_R, N_Q, N_M)), 0, 1)
        np.savez_compressed(d / f"{spec.name}.npz", scores=scores)
    return A.Run(tmp_path, datasets=("squad2",))


def test_admissible_budget_indices():
    assert A.op_indices("count", 512) == [0, 1, 2, 3]
    assert [OPS[i] for i in A.op_indices("budget", 512)] == ["B512", "B1024", "B2048"]
    assert [OPS[i] for i in A.op_indices("budget", 512, admissible=False)] == [f"B{b}" for b in BUDGETS]


def test_claim_diff_sign_and_labels(tmp_path):
    run = _write_run(tmp_path, lambda c, o: 0.8 if c == "fixed-128" else 0.5)
    claim = next(c for c in A.preregistered_claims() if c.cid == "P1")
    diffs = A.claim_diffs(run, claim, "count")
    diff, labels = diffs["squad2"]
    assert diff.shape == (N_Q, N_R * len(KS) * N_M) and len(labels) == diff.shape[1]
    assert diff.mean() == pytest.approx(0.3, abs=0.01)  # A (fixed-128) minus B (fixed-512)
    assert labels[0] == ("lucene-k1.5-b0.75-stem", "k1", "hit_strict")


def test_protocol_contrast_detects_constructed_artefact(tmp_path):
    # Under count-matching fixed-512 wins everywhere; under budget-matching fixed-128 wins everywhere.
    def effect(c, o):
        count = o < len(KS)
        if c == "fixed-512":
            return 0.8 if count else 0.4
        if c == "fixed-128":
            return 0.4 if count else 0.8
        return 0.5

    run = _write_run(tmp_path, effect)
    claim = next(c for c in A.preregistered_claims() if c.cid == "P1")
    res = A.protocol_contrast(run, claim, side=-1, reps=200, joint_reps=50)
    assert res["count"]["support_B"] == 1.0 and res["budget"]["support_B"] == 0.0
    assert res["estimate"] == pytest.approx(1.0)
    assert A.hypothesis_verdict(res["estimate"], *res["ci95"], 0.20) == "supported"


def test_null_world_gives_falsified_or_inconclusive(tmp_path):
    run = _write_run(tmp_path, lambda c, o: 0.5)
    claim = next(c for c in A.preregistered_claims() if c.cid == "P1")
    res = A.protocol_contrast(run, claim, side=-1, reps=200, joint_reps=50)
    assert abs(res["estimate"]) < 0.2
    assert A.hypothesis_verdict(res["estimate"], *res["ci95"], 0.20) in {"falsified", "inconclusive"}
