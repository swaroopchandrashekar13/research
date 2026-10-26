"""Metrics-only release form and package verification: what is removed, what is kept, and that every kind of leak
fails the verification."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from ragmv import analyze_generation as AG
from ragmv import metrics_form as MF

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import stage_release as SR  # noqa: E402

E2 = ROOT / "experiments" / "E2_generation" / "runs" / "qwen3-4b-kaggle-gpu"
ANSWER = "the forty-two numbered passages of the treaty"
ROW = {"job_id": "squad2:q1|fixed-128|count5", "qid": "squad2:q1", "chunking": "fixed-128", "op": "count5",
       "answers": [ANSWER], "prompt_sha256": "0" * 64, "context_words": 640,
       "retrieval": {"hit_strict": 1.0, "hit_lenient": 1.0, "coverage": 0.5}, "status": "ok",
       "response": "Unanswerable.", "latency_s": 1.2, "model_version": "m@r/f.gguf", "finish_reason": "stop",
       "usage": {"prompt_token_count": 10, "candidates_token_count": 2}, "model": "m", "hardware": "cpu",
       "called_utc": "2026-10-19T00:00:00Z", "em": 0.0, "f1": 0.0}
needs_git = pytest.mark.skipif(shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
needs_logs = pytest.mark.skipif(not (E2 / "squad2" / "generations.jsonl").exists(),
                                reason="needs the full generation logs (not part of the metrics-only package)")


def test_metrics_row_drops_text_and_keeps_metrics():
    m = MF.to_metrics(ROW)
    assert not set(m) & set(MF.DROP) and m["response_unanswerable"] is True
    assert {k: m[k] for k in ("qid", "em", "f1", "retrieval", "usage")} == {k: ROW[k] for k in ("qid", "em", "f1", "retrieval", "usage")}
    MF.check_row(m)


@pytest.mark.parametrize("change", [lambda r: r.update(question="What?"), lambda r: r.update(extra=1)])
def test_unreviewed_field_stops_the_conversion(change):
    row = dict(ROW)
    change(row)
    with pytest.raises(MF.MetricsFormError, match="unreviewed"):
        MF.to_metrics(row)


def test_schema_rejects_text_in_a_metrics_row():
    m = MF.to_metrics(ROW)
    for bad in ({**m, "response": "x"}, {**m, "retrieval": {"hit_strict": 1.0}}, {**m, "em": "1"},
                {**m, "usage": {"prompt_token_count": 1, "note": "x"}}):
        with pytest.raises(MF.MetricsFormError):
            MF.check_row(bad)


def test_incomplete_log_is_not_converted(tmp_path):
    p = tmp_path / "generations.jsonl"
    p.write_text(json.dumps(ROW) + "\n" + json.dumps(ROW)[:20])
    with pytest.raises(MF.MetricsFormError, match="incomplete"):
        MF.convert_log(p)


@needs_logs
def test_analysis_of_the_metrics_form_equals_the_analysis_of_the_logs(tmp_path):
    run = tmp_path / "run"
    for d in ("squad2", "cuad"):
        (run / d).mkdir(parents=True)
        (run / d / "generations.metrics.jsonl").write_text(MF.convert_log(E2 / d / "generations.jsonl"))
    full = tmp_path / "full"
    for d in ("squad2", "cuad"):
        (full / d).mkdir(parents=True)
        shutil.copy(E2 / d / "generations.jsonl", full / d / "generations.jsonl")
    a, b = AG.analyse(full, reps=50), AG.analyse(run, reps=50)
    assert a == b and a["datasets"]["squad2"]["diagnostics"]["integrity"]["segments"] == ["generations.jsonl"]


def _package(tmp_path, extra=None, metrics_row=None):
    row = metrics_row or MF.to_metrics(ROW)
    files = {"README.md": b"read me\n", "PACKAGE.md": b"p\n", "LICENSE-DATA.md": b"l\n",
             "experiments/E2_generation/runs/r/squad2/generations.metrics.jsonl": (json.dumps(row) + "\n").encode(),
             "experiments/E2_generation/runs/r/squad2/jobs_meta.json": json.dumps({"qids": ["squad2:q1"]}).encode()}
    files.update(extra or {})
    z = tmp_path / "p.zip"
    SR.write_zip(files, z)
    src = tmp_path / "src" / "experiments" / "E2_generation" / "runs" / "r" / "squad2"
    src.mkdir(parents=True, exist_ok=True)
    (src / "generations.jsonl").write_text(json.dumps(ROW) + "\n")
    return z, tmp_path / "src"


def _failed(checks):
    return [n for n, ok, _ in checks if not ok]


def test_clean_package_passes(tmp_path):
    z, src = _package(tmp_path)
    assert _failed(SR.verify(z, src)) == []


@pytest.mark.parametrize("extra, expect", [
    ({"README.md": f"quoting: {ANSWER.upper()}\n".encode()}, "answer or response string"),
    ({"experiments/E1/runs/x/q.json": json.dumps({"response": "x"}).encode()}, "text-carrying key"),
    ({"tools/x.py": b"p = '/ho" + b"me/someone/data'\n"}, "private absolute paths"),
    ({"tools/y.py": b"k = 'AIza" + b"A" * 35 + b"'\n"}, "credential"),
    ({"notes/unreviewed.txt": b"x\n"}, "allowed by a release rule"),
    ({"experiments/E2_generation/runs/r/squad2/generations.jsonl": b"{}\n"}, "generation log with text"),
    ({"src/ragmv/__pycache__/a.pyc": b"x"}, "caches"),
])
def test_each_leak_fails_verification(tmp_path, extra, expect):
    z, src = _package(tmp_path, extra)
    assert any(expect in n for n in _failed(SR.verify(z, src))), expect


def test_schema_violation_and_digest_mismatch_fail(tmp_path):
    z, src = _package(tmp_path, metrics_row={**MF.to_metrics(ROW), "answers": [ANSWER]})
    assert any("allowlisted fields" in n for n in _failed(SR.verify(z, src)))
    z, src = _package(tmp_path)
    import zipfile
    with zipfile.ZipFile(z, "a") as f:
        f.writestr(f"{SR.TOP}/README.md.extra", b"x")
    assert any(SR.SUMS in n for n in _failed(SR.verify(z, src)))


def test_unsafe_entry_is_refused(tmp_path):
    import zipfile
    z = tmp_path / "bad.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr(f"{SR.TOP}/../evil.txt", b"x")
    with pytest.raises(SR.StageError, match="unsafe"):
        SR.read_zip(z)


@needs_git
def test_every_repository_file_has_a_release_rule_and_the_plan_holds_no_log_text():
    files = SR.plan(ROOT, allow_dirty=True)
    assert not [p for p in files if p.endswith("generations.jsonl")]
    assert all(p in files for p in SR.PACKAGE_FILES)
    listed = [line.split(None, 1)[1] for line in files[SR.PROTECTED].decode().splitlines()
              if line.strip() and not line.startswith("#")]
    assert listed and all(p in files for p in listed)


@needs_git
def test_build_refuses_a_dirty_tree_without_the_flag(tmp_path):
    if not subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        pytest.skip("the working tree is clean")
    with pytest.raises(SR.StageError, match="uncommitted"):
        SR.plan(ROOT, allow_dirty=False)
