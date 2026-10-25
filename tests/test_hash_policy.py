"""Hash policy: removed values stay removed in historical evidence, markers are confined to registered records,
and validators never pass provenance that rests on a removed value. The check is read-only."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ragmv import provenance as PV

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_hash_policy as CH  # noqa: E402
import validate_artifacts as VA  # noqa: E402

needs_git = pytest.mark.skipif(shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout")


@needs_git
def test_repository_follows_the_hash_policy():
    assert CH.main() == 0


def test_check_tool_has_no_write_mode():
    src = (ROOT / "tools" / "check_hash_policy.py").read_text()
    assert "write_bytes" not in src and "write_text" not in src and "--apply" not in src


def test_markers_are_allowed_only_in_registered_places():
    assert CH.marker_allowed("experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu/cuad/manifest.json")
    assert CH.marker_allowed("experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/UPLOAD_SHA256")
    assert not CH.marker_allowed("experiments/E3_semantic_dense/runs/new-run/cuad/manifest.json")
    assert not CH.marker_allowed("manuscript/main.tex")


def test_hash_like_values_are_detected_and_question_ids_are_kept():
    digest, qid = "a1" * 32, "b2" * 20
    assert CH.hash_like(f'"config_sha256": "{digest}"', set()) == [digest]
    assert CH.hash_like(f'"qid": "qasper:{qid}"', {qid}) == []
    assert CH.hash_like('"value": 1.0864e-05, "n": 1234567', set()) == []


def test_historical_binding_uses_run_name_and_record_time(tmp_path):
    key = "experiments/E1_retrieval_multiverse/runs/confirmatory-20261018"
    run = tmp_path / key
    assert PV.historical_record(run, "cuad", PV.HISTORICAL_RUNS[key]["cuad"])
    assert not PV.historical_record(run, "cuad", "2026-10-18T00:00:00+00:00")
    assert not PV.historical_record(tmp_path / "experiments/E1_retrieval_multiverse/runs/other", "cuad",
                                    PV.HISTORICAL_RUNS[key]["cuad"])
    assert PV.run_key(tmp_path / "not-a-run") is None


def test_generation_identity_never_passes_removed_values():
    rows = [{"prompt_sha256": PV.DIGEST_REMOVED, "model_version": f"Qwen/Qwen3-4B-GGUF{PV.REVISION_REMOVED}/f.gguf"}]
    meta = {"local_model": ["Qwen/Qwen3-4B-GGUF", PV.MODEL_REVISION_REMOVED, "f.gguf", PV.MODEL_FILE_DIGEST_REMOVED, True]}
    bad, gaps = VA.generation_identity(rows, meta, historical=True)
    assert not bad and len(gaps) == 4  # structurally allowed, provenance incomplete
    bad, _ = VA.generation_identity(rows, meta, historical=False)
    assert len(bad) == 4  # the same markers outside a historical record are failures
    ok_rows = [{"prompt_sha256": "c3" * 32, "model_version": "repo@" + "d4" * 6 + "/f.gguf"}]
    assert VA.generation_identity(ok_rows, {"local_model": None}, historical=False) == ([], [])
    bad, _ = VA.generation_identity([{"prompt_sha256": "redacted: other", "model_version": None}], {}, False)
    assert bad


def test_provenance_rows_are_never_pass():
    rep = VA.Report()
    rep.provenance("x", ["a gap"])
    rep.provenance("y", [])
    assert [r[0] for r in rep.rows] == ["INCOMPLETE", "NOTE", "COMPLETE"] and rep.incomplete == 1 and rep.failed == 0


@needs_git
def test_validator_release_gate_fails_on_incomplete_provenance(tmp_path):
    out = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "validate_artifacts.py"), "--require-provenance",
                          "--report", str(tmp_path / "r.md")], capture_output=True, text=True)
    assert out.returncode == 1 and "INCOMPLETE" in (tmp_path / "r.md").read_text()
    assert json.dumps(PV.HISTORICAL_RUNS)  # registry is plain data
