import json
import os
from pathlib import Path

import numpy as np
import pytest

from ragmv import data as D
from ragmv import generate as G

RAW = Path(os.environ.get("RAGMV_DATA_ROOT") or Path(__file__).resolve().parents[1] / "data" / "raw")
RUN = Path(__file__).resolve().parents[1] / "experiments" / "E1_retrieval_multiverse" / "runs" / "confirmatory-20261018"


def test_squad_normalisation_em_f1():
    assert G.normalize_answer("The  Normans!") == "normans"
    assert G.exact_match("the Normans", ["Normans", "x"]) == 1.0
    assert G.token_f1("in France", ["France"]) == pytest.approx(2 * 0.5 * 1 / 1.5)
    assert G.token_f1("unanswerable", ["France"]) == 0.0
    assert G.token_f1("", [""]) == 1.0


def test_select_passages_count_and_exact_budget():
    cd, ws, we = np.array([0, 1, 0]), np.array([0, 0, 100]), np.array([50, 60, 150])
    assert G.select_passages([1, 0, 2], cd, ws, we, "count", 2) == [(1, 0, 60), (0, 0, 50)]
    sel = G.select_passages([1, 0, 2], cd, ws, we, "budget", 130)
    assert sel == [(1, 0, 60), (0, 0, 50), (0, 100, 120)] and sum(e - s for _, s, e in sel) == 130


def test_prompt_is_deterministic_and_ordered():
    p = G.build_prompt("Who?", ["alpha", "beta"])
    assert p == G.build_prompt("Who?", ["alpha", "beta"])
    assert p.index("[1] alpha") < p.index("[2] beta") and p.endswith("Question: Who?\nAnswer:")


def test_resume_skips_only_successful_rows(tmp_path):
    path = tmp_path / "generations.jsonl"
    path.write_text(json.dumps({"job_id": "a", "status": "ok"}) + "\n" + json.dumps({"job_id": "b", "status": "error"}) + "\n")
    assert G.done_ids(path) == {"a"}


def test_dry_run_writes_no_key(tmp_path, monkeypatch):
    if not (RAW / "covidqa").exists():
        pytest.skip("raw data not downloaded")
    sentinel = "SENTINEL-KEY-should-never-appear"
    monkeypatch.setenv(G.KEY_ENV, sentinel)
    assert G.main(["--dataset", "covidqa", "--out", str(tmp_path), "--per-dataset", "3", "--dry-run",
                   "--data-root", str(RAW)]) == 0
    for f in tmp_path.rglob("*"):
        if f.is_file():
            assert sentinel not in f.read_text()


def test_tier2_retrieval_matches_confirmatory_run():
    """The text sent to the model must come from exactly the retrieval E1 measured."""
    if not (RAW / "squad2").exists() or not (RUN / "squad2" / "fixed-128.npz").exists():
        pytest.skip("data or confirmatory run not present")
    docs, queries = D.load("squad2", RAW)
    sample = G.sample_queries(queries, D.split_documents(len(docs)), 5)
    jobs = G.build_jobs(docs, sample)
    qids = json.loads((RUN / "squad2" / "queries.json").read_text())["qids"]
    run_cfg = json.loads((RUN / "squad2" / "manifest.json").read_text())["config"]
    r_idx = run_cfg["retrievers"].index(G.RETRIEVER)
    op_idx = {"count5": run_cfg["ops"].index("k5"), "budget1024": run_cfg["ops"].index("B1024")}
    for j in jobs:
        stored = np.load(RUN / "squad2" / f"{j['chunking']}.npz", allow_pickle=False)["scores"][r_idx, qids.index(j["qid"]), op_idx[j["op"]]]
        assert [float(x) for x in stored] == pytest.approx(list(j["retrieval"].values()), abs=1e-3)


class _FakeModels:
    def __init__(self):
        self.configs = []

    def generate_content(self, model, contents, config):
        from types import SimpleNamespace

        self.configs.append(config)
        return SimpleNamespace(text=" Normans \n", model_version="served-model-2", usage_metadata=None,
                               candidates=[SimpleNamespace(finish_reason="STOP")])


def test_call_model_records_served_version_and_thinking_level():
    pytest.importorskip("google.genai")
    from types import SimpleNamespace

    client = SimpleNamespace(models=_FakeModels())
    res = G.call_model(client, "requested-model", "prompt", "minimal")
    assert res["status"] == "ok" and res["response"] == "Normans" and res["model_version"] == "served-model-2"
    cfg = client.models.configs[-1]
    assert cfg.temperature == 0.0 and cfg.seed == 7 and str(cfg.thinking_config.thinking_level).endswith("MINIMAL")
    G.call_model(client, "requested-model", "prompt", None)
    assert client.models.configs[-1].thinking_config is None


def _synthetic_run(root: Path, effect: float, n: int = 40, seed: int = 0):
    from ragmv import analyze_generation as A

    rng = np.random.default_rng(seed)
    for ds in ("squad2", "cuad"):
        lines = []
        for q in range(n):
            base = rng.uniform(0.2, 0.8)
            for claim, (a, b) in A.CLAIMS.items():
                for chunking in (a, b):
                    for op in A.OPS:
                        # A gains `effect` relative to B under budget only -> DiD = effect
                        f1 = base + (effect if (chunking == a and op == "budget1024") else 0.0) + rng.normal(0, 0.05)
                        row = {"job_id": f"{ds}:{q}|{chunking}|{op}", "qid": f"{ds}:{q}", "chunking": chunking,
                               "op": op, "status": "ok", "response": "x", "f1": f1, "em": float(f1 > 0.5),
                               "retrieval": {"hit_strict": 1.0, "hit_lenient": 1.0, "coverage": f1},
                               "model": "m", "model_version": "m", "finish_reason": "STOP"}
                        lines.append(json.dumps({**row, "status": "error", "f1": None}))  # superseded attempt
                        lines.append(json.dumps(row))
        (root / ds).mkdir(parents=True)
        # one incomplete query: only a single job present
        lines.append(json.dumps({**json.loads(lines[-1]), "qid": f"{ds}:extra", "chunking": "x", "op": "count5",
                                 "job_id": f"{ds}:extra|x|count5"}))
        (root / ds / "generations.jsonl").write_text("\n".join(lines) + "\n")


def test_generation_analysis_detects_known_reversal(tmp_path):
    from ragmv import analyze_generation as A

    _synthetic_run(tmp_path / "pos", effect=0.2)
    res = A.analyse(tmp_path / "pos", reps=500)
    assert res["datasets"]["squad2"]["n_complete_queries"] == 40
    for claim in A.CLAIMS:
        pooled = res["pooled"][claim]["f1"]
        assert pooled["did"] == pytest.approx(0.2, abs=0.03) and pooled["verdict"] == "carries over"
    _synthetic_run(tmp_path / "null", effect=0.0, seed=3)  # seed 1 is a 5% false positive
    assert A.analyse(tmp_path / "null", reps=500)["pooled"]["P1"]["f1"]["verdict"] == "inconclusive"
    assert "carries over" in A.to_markdown(res)


def test_daily_quota_detected_beyond_message_truncation():
    pytest.importorskip("google.genai")
    from types import SimpleNamespace

    class _Quota:
        def generate_content(self, model, contents, config):
            raise RuntimeError("429 RESOURCE_EXHAUSTED. " + "x" * 400 + " 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier'")

    res = G.call_model(SimpleNamespace(models=_Quota()), "m", "prompt", "minimal", max_retries=2)
    assert res["status"] == "quota_exhausted" and len(res["error"]) < 350


class _FakeLlama:
    def __init__(self, n_tokens=100):
        self.n_tokens, self.prompts = n_tokens, []

    def tokenize(self, b, add_bos=False, special=True):
        return [0] * self.n_tokens

    def create_completion(self, text, **kw):
        self.prompts.append((text, kw))
        return {"choices": [{"text": " Normans", "finish_reason": "stop"}],
                "usage": {"prompt_tokens": self.n_tokens, "completion_tokens": 2}}


def test_local_backend_prompt_format_and_greedy_decoding():
    llm = _FakeLlama()
    res = G.call_local(llm, "qwen3-4b-q4_k_m", "Passages: ...", n_ctx=8192)
    text, kw = llm.prompts[-1]
    assert res["status"] == "ok" and res["response"] == "Normans" and res["model_version"].startswith("Qwen/Qwen3-4B-GGUF@")
    assert text.startswith("<|im_start|>system\n" + G.SYSTEM) and text.endswith("<think>\n\n</think>\n\n")
    assert kw["temperature"] == 0.0 and kw["top_k"] == 1 and kw["max_tokens"] == G.MAX_OUTPUT_TOKENS
    G.call_local(llm, "qwen2.5-1.5b-instruct-q4_k_m", "Passages: ...", n_ctx=8192)
    assert llm.prompts[-1][0].endswith("<|im_start|>assistant\n")  # non-thinking model: no think block
    assert G.call_local(_FakeLlama(n_tokens=8000), "qwen3-4b-q4_k_m", "x", n_ctx=8192)["status"] == "error"


def test_hardware_tag_records_cpu_build():
    pytest.importorskip("llama_cpp")
    tag = G.hardware_tag(0)
    assert tag.startswith("cpu|") and "llama_cpp_python" in tag and tag.endswith("n_gpu_layers 0")


def test_half_written_last_line_needs_explicit_recovery(tmp_path):
    path = tmp_path / "generations.jsonl"
    path.write_text(json.dumps({"job_id": "a", "status": "ok"}) + "\n" + '{"job_id": "b", "sta')
    with pytest.raises(G.JsonlIntegrityError, match="incomplete final record"):
        G.read_rows(path)
    assert len(G.read_rows(path, recover_tail=True)) == 1
    assert G.done_ids(path) == {"a"}  # progress counters tolerate the tail explicitly
    assert G.append_segment(tmp_path).name == "generations.seg-002.jsonl"  # never appended onto the fragment


def test_malformed_interior_line_is_rejected_with_its_line_number(tmp_path):
    path = tmp_path / "generations.jsonl"
    path.write_text(json.dumps({"job_id": "a", "status": "ok"}) + "\n{oops\n" + json.dumps({"job_id": "c"}) + "\n")
    with pytest.raises(G.JsonlIntegrityError, match=r"generations.jsonl:2: malformed"):
        G.read_rows(path, recover_tail=True)
