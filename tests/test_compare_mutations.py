"""Mutation tests: every kind of corruption of a recomputed result or of an input identity must fail its check."""
import copy
import json
import sys
from pathlib import Path

import pytest

from ragmv import analyze as A
from ragmv import fetch as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import compare_results as C  # noqa: E402

BASE = {"H1": {"estimate": 0.711, "ci95": [0.648, 0.819], "verdict": "supported"},
        "verdict_shares": {"P1": {"count": {"support_A": 0.1, "n_universes": 768}}},
        "validation": {"legacy_limitations": ["x"]}, "code_sha256": "a" * 64}


def _mutated(change):
    new = copy.deepcopy(BASE)
    change(new)
    return new


def test_identical_results_pass():
    res = C.compare(BASE, copy.deepcopy(BASE))
    assert not C.failed(res) and res["identical"] > 0


@pytest.mark.parametrize("name, change, bucket", [
    ("wrong copied estimate", lambda r: r["H1"].update(estimate=0.712), "different"),
    ("altered confidence interval", lambda r: r["H1"]["ci95"].__setitem__(0, 0.6481), "different"),
    ("changed verdict", lambda r: r["H1"].update(verdict="inconclusive"), "verdict_changes"),
    ("missing key", lambda r: r["verdict_shares"]["P1"]["count"].pop("n_universes"), "missing_scientific"),
    ("NaN", lambda r: r["H1"].update(estimate=float("nan")), "nonfinite"),
    ("infinite", lambda r: r["verdict_shares"]["P1"]["count"].update(support_A=float("inf")), "nonfinite"),
    ("integer changed to text", lambda r: r["verdict_shares"]["P1"]["count"].update(n_universes="768"), "different"),
    ("tiny float drift above tolerance", lambda r: r["H1"].update(estimate=0.711 + 1e-9), "different"),
])
def test_each_mutation_fails(name, change, bucket):
    res = C.compare(BASE, _mutated(change))
    assert C.failed(res) and res[bucket], name


def test_metadata_may_differ_but_not_hide_science():
    new = _mutated(lambda r: (r.update(code_sha256="b" * 64), r["validation"].update(legacy_limitations=[])))
    assert not C.failed(C.compare(BASE, new))
    with pytest.raises(ValueError, match="refusing to ignore scientific"):
        C.compare(BASE, BASE, ignore=("H1",))


def test_cli_rejects_tolerance_inflation(tmp_path, capsys):
    p = tmp_path / "a.json"
    p.write_text(json.dumps(BASE))
    with pytest.raises(SystemExit):
        C.main([str(p), str(p), "--float-atol", "1e-3"])
    assert "no tolerance inflation" in capsys.readouterr().err


def test_wrong_input_identity_fails(tmp_path):
    run = ROOT / "experiments/E1_retrieval_multiverse/runs/confirmatory-20261018"
    protected = ROOT / "docs/remediation/PROTECTED_SHA256.txt"
    digest = next(line.split()[0] for line in protected.read_text().splitlines()
                  if line.endswith("confirmatory-20261018/cuad/manifest.json"))
    good = {"consumed_inputs_sha256": {"cuad/manifest.json": digest}}
    assert C.check_inputs(good, protected, run) == []
    bad = {"consumed_inputs_sha256": {"cuad/manifest.json": "0" * 64}}
    assert C.check_inputs(bad, protected, run) and C.check_inputs({}, protected, run)


def test_wrong_configuration_checksum_fails(tmp_path):
    from test_run_validation import _validate, write_run

    root = write_run(tmp_path)
    m = json.loads((root / "cuad" / "manifest.json").read_text())
    m["config_sha256"] = "f" * 64
    (root / "cuad" / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(A.RunValidationError, match="fingerprint"):
        _validate(root)


def test_wrong_dataset_checksum_fails(tmp_path):
    data = tmp_path / "data" / "raw" / "covidqa"
    data.mkdir(parents=True)
    (data / "COVID-QA.json").write_text("{}")
    manifest = tmp_path / "MANIFEST.yaml"
    manifest.write_text("datasets:\n  covidqa:\n    files:\n      - path: data/raw/covidqa/COVID-QA.json\n"
                        "        url: https://example.invalid/x\n        sha256: " + "0" * 64 + "\n")
    with pytest.raises(F.IntegrityError, match="does not match"):
        F.verify_consumed("covidqa", tmp_path / "data" / "raw", manifest)
