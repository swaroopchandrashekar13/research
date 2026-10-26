"""Strict JSONL, interruption/resume through a new segment, immutable run identity, locking,
non-mutating dry runs and truthful exit codes, exercised end to end with a synthetic dataset and a fake model."""
import hashlib
import json
import sys
import types

import numpy as np
import pytest
import yaml

from ragmv import analyze_generation as AG
from ragmv import generate as G
from ragmv.integrity import RunLock


def _synthetic_squad(tmp_path, n_docs=10):
    rng = np.random.default_rng(0)
    data = []
    for d in range(n_docs):
        words = [f"w{d}_{i}" for i in range(320)]
        text = " ".join(words)
        qas = []
        for k in range(3):
            i = int(rng.integers(0, 300))
            ans = " ".join(words[i:i + 2])
            qas.append({"id": f"{d:02d}{k}", "question": f"what is {words[i]} {words[i + 1]}?",
                        "answers": [{"text": ans, "answer_start": text.index(ans)}], "is_impossible": False})
        data.append({"title": f"doc{d}", "paragraphs": [{"context": text, "qas": qas}]})
    raw = tmp_path / "data" / "raw" / "squad2"
    raw.mkdir(parents=True)
    blob = json.dumps({"data": data}).encode()
    (raw / "dev-v2.0.json").write_bytes(blob)
    man = tmp_path / "MANIFEST.yaml"
    man.write_text(yaml.safe_dump({"datasets": {"squad2": {"files": [
        {"url": "unused", "path": "data/raw/squad2/dev-v2.0.json", "sha256": hashlib.sha256(blob).hexdigest()}]}}}))
    return tmp_path / "data" / "raw", man


class FakeLlama:
    calls = 0
    fail = False

    def __init__(self, **kw):
        self.kw = kw

    def tokenize(self, b, add_bos=False, special=True):
        return [0] * (10_000 if FakeLlama.fail else len(b) // 5)

    def create_completion(self, text, **kw):
        FakeLlama.calls += 1
        q = text.split("Question: ")[-1].split("?")[0].replace("what is ", "")
        return {"choices": [{"text": " " + q, "finish_reason": "stop"}], "usage": {"prompt_tokens": 1, "completion_tokens": 2}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    data_root, man = _synthetic_squad(tmp_path)
    monkeypatch.setitem(sys.modules, "llama_cpp", types.SimpleNamespace(Llama=FakeLlama))
    monkeypatch.setattr(G, "local_model_path", lambda name, d: tmp_path / "model.gguf")
    monkeypatch.setattr(G, "hardware_tag", lambda n: f"test-cpu|x86_64|fake|n_gpu_layers {n}")
    FakeLlama.fail = False
    base = ["--backend", "llama", "--model", "qwen3-4b-q4_k_m", "--dataset", "squad2", "--per-dataset", "3",
            "--data-root", str(data_root), "--data-manifest", str(man)]
    return types.SimpleNamespace(tmp=tmp_path, base=base, data_root=data_root, man=man)


def _digests(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.iterdir()) if p.is_file()}


def test_full_interruption_and_resume_cycle(env, capsys):
    out = env.tmp / "run"
    args = env.base + ["--out", str(out)]
    assert G.main(args + ["--max-calls", "5"]) == G.EXIT_INCOMPLETE  # truthful: 5 of 24 jobs
    d = out / "squad2"
    assert len((d / "generations.jsonl").read_text().splitlines()) == 5
    meta0 = (d / "jobs_meta.json").read_bytes()
    ident = json.loads((d / "run_identity.json").read_text())
    assert ident["identity"]["prompt"]["system"] == G.SYSTEM and "git" not in json.dumps(ident)
    with open(d / "generations.jsonl", "a") as f:  # the process is killed in the middle of a record
        f.write('{"job_id": "squad2:x|fixed-128|count5", "sta')
    damaged = hashlib.sha256((d / "generations.jsonl").read_bytes()).hexdigest()

    assert G.main(args) == G.EXIT_CANNOT_START  # recovery is not implicit
    assert "incomplete final record" in capsys.readouterr().err
    assert not (d / "generations.seg-002.jsonl").exists()

    assert G.main(args + ["--recover-incomplete-tail"]) == G.EXIT_COMPLETE
    assert hashlib.sha256((d / "generations.jsonl").read_bytes()).hexdigest() == damaged  # original kept
    seg = (d / "generations.seg-002.jsonl").read_text().splitlines()
    assert len(seg) == 19 and all(json.loads(x)["status"] == "ok" for x in seg)
    assert (d / "jobs_meta.json").read_bytes() == meta0  # original start metadata preserved
    sessions = [json.loads(x) for x in (d / "sessions.jsonl").read_text().splitlines()]
    assert [s["exit_code"] for s in sessions] == [G.EXIT_INCOMPLETE, G.EXIT_COMPLETE]
    assert sessions[1]["rejected_tail_records"] and sessions[1]["already_done"] == 5

    with pytest.raises(G.JsonlIntegrityError):
        AG.analyse(out, reps=50)
    res = AG.analyse(out, reps=50, recover_tail=True)
    integ = res["datasets"]["squad2"]["diagnostics"]["integrity"]
    assert integ["accepted"] == 24 and integ["complete"] == 24 and len(integ["rejected"]) == 1
    assert integ["raw_lines"] == 25 and integ["segments"] == ["generations.jsonl", "generations.seg-002.jsonl"]
    assert res["datasets"]["squad2"]["n_complete_queries"] == 3


def test_identity_mismatch_is_refused_without_modification(env, capsys):
    out = env.tmp / "run"
    assert G.main(env.base + ["--out", str(out), "--max-calls", "3"]) == G.EXIT_INCOMPLETE
    before = _digests(out / "squad2")
    for extra in (["--n-ctx", "4096"], ["--threads", "2"], ["--n-gpu-layers", "-1"]):
        assert G.main(env.base + ["--out", str(out)] + extra) == G.EXIT_CANNOT_START
        assert _digests(out / "squad2") == before
    assert "different run identity" in capsys.readouterr().err


def test_changed_input_bytes_are_refused(env):
    out = env.tmp / "run"
    f = env.data_root / "squad2" / "dev-v2.0.json"
    f.write_bytes(f.read_bytes().replace(b"w0_1 ", b"w0_X ", 1))
    assert G.main(env.base + ["--out", str(out)]) == G.EXIT_CANNOT_START
    assert not out.exists()


def test_legacy_run_directory_is_never_extended(env):
    d = env.tmp / "legacy" / "squad2"
    d.mkdir(parents=True)
    (d / "generations.jsonl").write_text(json.dumps({"job_id": "a|b|c", "qid": "a", "chunking": "b", "op": "c",
                                                     "status": "ok"}) + "\n")
    before = _digests(d)
    assert G.main(env.base + ["--out", str(env.tmp / "legacy")]) == G.EXIT_CANNOT_START
    assert _digests(d) == before


def test_dry_run_writes_nothing(env, capsys):
    out = env.tmp / "dry"
    assert G.main(env.base + ["--out", str(out), "--dry-run"]) == 0
    assert not out.exists() and '"jobs": 24' in capsys.readouterr().out


def test_concurrent_writer_is_refused(env):
    out = env.tmp / "run"
    with RunLock(out / "squad2"):
        assert G.main(env.base + ["--out", str(out)]) == G.EXIT_CANNOT_START
    assert not (out / "squad2" / "generations.jsonl").exists()


def test_malformed_interior_record_names_the_line(env, capsys):
    out = env.tmp / "run"
    assert G.main(env.base + ["--out", str(out), "--max-calls", "4"]) == G.EXIT_INCOMPLETE
    p = out / "squad2" / "generations.jsonl"
    lines = p.read_text().splitlines()
    lines.insert(2, "{not json")
    p.write_text("\n".join(lines) + "\n")
    assert G.main(env.base + ["--out", str(out), "--recover-incomplete-tail"]) == G.EXIT_CANNOT_START
    assert "generations.jsonl:3: malformed JSON record" in capsys.readouterr().err


def test_failed_jobs_give_an_incomplete_exit_code(env):
    FakeLlama.fail = True  # every prompt overflows the context: error rows
    out = env.tmp / "run"
    assert G.main(env.base + ["--out", str(out)]) == G.EXIT_INCOMPLETE
    rows = [json.loads(x) for x in (out / "squad2" / "generations.jsonl").read_text().splitlines()]
    assert len(rows) == 24 and all(r["status"] == "error" for r in rows)


def test_job_id_must_be_the_record_key(tmp_path):
    row = {"job_id": "q|fixed-128|count5", "qid": "q", "chunking": "fixed-512", "op": "count5", "status": "ok"}
    with pytest.raises(G.JsonlIntegrityError, match="does not match"):
        G.summarize_rows([row])


def test_counts_keep_raw_superseded_complete_and_accepted_apart():
    rows = [{"job_id": "q|a|o", "qid": "q", "chunking": "a", "op": "o", "status": s} for s in ("error", "ok", "ok")]
    c = G.summarize_rows(rows)["counts"]
    assert c == {"complete": 2, "accepted": 1, "superseded": 2, "duplicate_ok": 1,
                 "status_counts": {"error": 1, "ok": 2}}
