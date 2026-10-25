"""Second hash-removal pass (2026-10-25): historical evidence carries no machine-readable hash values.

Synthetic values are built at run time so that this file itself contains no hexadecimal identifiers.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import redact_historical_hashes as rh  # noqa: E402

SHA256 = "a1" * 32
SHA1 = "b2" * 20


def test_digest_fields_and_model_revisions_are_replaced():
    row = {"qid": "q1", "prompt_sha256": SHA256, "model_version": f"Qwen/Qwen3-4B@{SHA1}|q4", "f1": 0.5}
    text = json.dumps(row) + "\n" + json.dumps({"config_sha256": SHA256}) + "\n"
    new, n = rh.redact_text(text)
    assert n == 3
    first, second = (json.loads(line) for line in new.splitlines())
    assert first["prompt_sha256"] == rh.DIGEST and second["config_sha256"] == rh.DIGEST
    assert first["model_version"] == f"Qwen/Qwen3-4B@{rh.REV}|q4"
    assert first["qid"] == "q1" and first["f1"] == 0.5  # everything else unchanged


def test_jobs_meta_lists_are_replaced():
    text = json.dumps({"model": [SHA1, SHA256]}, indent=2)
    new, n = rh.redact_text(text)
    assert n == 2
    assert json.loads(new)["model"] == ["redacted: model revision removed", "redacted: model file digest removed"]


def test_build_log_keeps_question_ids_numbers_and_words():
    qid = "c3" * 12
    text = f"ggml commit {SHA1[:7]}\nfile {SHA256}\nquery {qid}\nsize 1234567 bytes, cafe added\n"
    new, n = rh.redact_log(text, keep={qid})
    assert n == 2
    assert new == f"ggml commit [hash removed]\nfile [hash removed]\nquery {qid}\nsize 1234567 bytes, cafe added\n"


@pytest.mark.skipif(shutil.which("git") is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_historical_evidence_contains_no_hash_values():
    assert rh.main(["--check"]) == 0
