"""Plotted coordinates come from the validated results (dumbbells) or match the analysis' own CIs."""
import json

import numpy as np

from ragmv import analyze as A
from ragmv import figures as Fg
from ragmv import stats as S

from test_run_validation import write_run


def test_dumbbell_plots_exactly_the_stored_shares(tmp_path):
    root = write_run(tmp_path / "run", datasets=("squad2", "covidqa"))
    out = tmp_path / "a"
    assert A.main(["--run", str(root), "--out", str(out), "--label", "SMOKE", "--reps", "60", "--joint-reps", "5"]) == 0
    res = json.loads((out / "results.json").read_text())
    Fg.verdict_dumbbell(res, Fg.DUMBBELL_CLAIMS, out, "SMOKE")
    coords = json.loads((out / "verdict_dumbbell.coords.json").read_text())["rows"]
    for cid, row in zip(Fg.DUMBBELL_CLAIMS, coords):
        v = res["verdict_shares"][cid]
        assert row["count"] == v["count"]["support_A"] - v["count"]["support_B"]
        assert row["budget"] == v["budget"]["support_A"] - v["budget"]["support_B"]
    assert (out / "verdict_dumbbell.pdf").stat().st_size > 0


def test_specification_curve_points_equal_per_universe_bootstrap_cis(tmp_path):
    root = write_run(tmp_path / "run", datasets=("squad2",))
    run = A.Run(root)
    Fg.specification_curve(run, "P1", "coverage", tmp_path, "SMOKE", reps=80, seed=7)
    pts = json.loads((tmp_path / "speccurve_P1_coverage.coords.json").read_text())["panels"]["squad2"]
    claim = next(c for c in A.planned_claims() if c.cid == "P1")
    for prot in ("count", "budget"):
        diff, labels = A.claim_diffs(run, claim, prot)["squad2"]
        mean, lo, hi, _ = S.paired_bootstrap_ci(diff, reps=80, seed=7)
        want = {tuple(lab): (m, l, h) for lab, m, l, h in zip(labels, mean, lo, hi) if lab[2] == "coverage"}
        got = {tuple(p["universe"]): (p["mean"], p["lo"], p["hi"]) for p in pts if p["protocol"] == prot}
        assert got.keys() == want.keys()
        for k in want:
            assert np.allclose(got[k], want[k])
    assert [p["mean"] for p in pts] == sorted(p["mean"] for p in pts)


def test_study1b_dumbbell_uses_stored_shares(tmp_path):
    share = {"support_A": 0.25, "support_B": 0.5}
    res = {"semantic_wins": {"S5-128": {"count": share, "budget": {"support_A": 0.1, "support_B": 0.7}}},
           "H5": {"count": {"support_A": 0.3, "support_B": 0.2}, "budget": {"support_A": 0.9, "support_B": 0.0}}}
    Fg.study1b_dumbbell(res, tmp_path, "SMOKE")
    rows = json.loads((tmp_path / "study1b_dumbbell.coords.json").read_text())["rows"]
    assert rows[0]["count"] == -0.25 and abs(rows[0]["budget"] + 0.6) < 1e-12 and rows[1]["budget"] == 0.9
