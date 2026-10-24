"""PY-001: runs are validated before analysis; partial/smoke inputs cannot pass as confirmatory analyses."""
import hashlib
import json

import numpy as np
import pytest

from ragmv import analyze as A
from ragmv import analyze1b as A1b
from ragmv import data as D
from ragmv.chunking import default_specs
from ragmv.retrieval import default_retrievers
from ragmv.run import OPS

N_DOCS, N_Q = 40, 30


def _config(dataset, split, chunkings, retrievers, study=None, max_queries=None):
    c = {"dataset": dataset, "split": split, "max_queries": max_queries, "chunkings": chunkings,
         "retrievers": retrievers, "ops": list(OPS), "metrics": ["hit_strict", "hit_lenient", "coverage"],
         "split_seed": 20261018, "split_frac_exploratory": 0.2}
    if study:
        c["study"] = study
    return c


def write_run(root, datasets=("squad2", "covidqa", "cuad", "qasper"), split="confirmatory", study=None,
              chunkings=None, retrievers=None, max_queries=None, seed=0):
    rng = np.random.default_rng(seed)
    chunkings = chunkings or [s.name for s in default_specs()]
    retrievers = retrievers or [r.name for r in default_retrievers()]
    mask = D.split_documents(N_DOCS)
    docs = np.flatnonzero(mask if split == "exploratory" else ~mask)
    for d in datasets:
        p = root / d
        p.mkdir(parents=True)
        cfg = _config(d, split, chunkings, retrievers, study, max_queries)
        doc_idx = [int(docs[i % len(docs)]) for i in range(N_Q)]
        (p / "queries.json").write_text(json.dumps({"qids": [f"{d}:q{i}" for i in range(N_Q)], "doc_idx": doc_idx}))
        manifest = {"status": "ok", "error": None, "config": cfg,
                    "config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
                    "n_documents": N_DOCS, "n_queries": N_Q, "chunk_stats": [
                        {"chunking": c, "chunk_words_mean": float(100 + 50 * i)} for i, c in enumerate(chunkings)],
                    "versions": {}, "platform": "test", "started_utc": "t"}
        (p / "manifest.json").write_text(json.dumps(manifest))
        for c in chunkings:
            s = rng.uniform(0, 1, (len(retrievers), N_Q, len(OPS), 3)).astype(np.float16)
            w = np.minimum(rng.integers(0, 3000, (len(retrievers), N_Q, len(OPS))), 128).astype(np.int32)
            np.savez_compressed(p / f"{c}.npz", scores=s, words=w, rr10=rng.uniform(0, 1, (len(retrievers), N_Q)).astype(np.float16))
    return root


CHUNKS1 = sorted({x for c in A.preregistered_claims() for x in (c.a, c.b)})


def _validate(root, label="CONFIRMATORY", study="1"):
    run = A.Run(root, study=study)
    if study == "1":
        return run.validate(label, CHUNKS1, A.full_design_study1())
    return run.validate(label, list(A1b.CHUNKINGS), {"chunkings": list(A1b.CHUNKINGS), "retrievers": list(A1b.RETRIEVERS)})


def test_complete_run_validates_and_reports_legacy_fields(tmp_path):
    v = _validate(write_run(tmp_path))
    assert v["split"] == "confirmatory" and any("'study'" in x for x in v["legacy_limitations"])


def test_partial_run_is_only_accepted_as_smoke(tmp_path):
    root = write_run(tmp_path, datasets=("squad2",))
    with pytest.raises(A.RunValidationError, match="datasets missing"):
        _validate(root)
    assert _validate(root, "SMOKE")["missing_datasets"] == ["covidqa", "cuad", "qasper"]


def test_max_queries_run_cannot_be_confirmatory(tmp_path):
    with pytest.raises(A.RunValidationError, match="max_queries"):
        _validate(write_run(tmp_path, max_queries=5))


def test_label_must_match_split(tmp_path):
    with pytest.raises(A.RunValidationError, match="label CONFIRMATORY"):
        _validate(write_run(tmp_path, split="exploratory"))


def test_mixed_splits_fail(tmp_path):
    write_run(tmp_path / "r", datasets=("squad2", "covidqa"))
    write_run(tmp_path / "x", datasets=("cuad",), split="exploratory")
    (tmp_path / "x" / "cuad").rename(tmp_path / "r" / "cuad")
    with pytest.raises(A.RunValidationError, match="mixed splits"):
        _validate(tmp_path / "r", "SMOKE")


def test_edited_config_fails_fingerprint(tmp_path):
    root = write_run(tmp_path)
    m = json.loads((root / "cuad" / "manifest.json").read_text())
    m["config"]["split_seed"] = 1
    (root / "cuad" / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(A.RunValidationError, match="fingerprint"):
        _validate(root)


def test_duplicate_query_ids_fail(tmp_path):
    root = write_run(tmp_path)
    q = json.loads((root / "qasper" / "queries.json").read_text())
    q["qids"][1] = q["qids"][0]
    (root / "qasper" / "queries.json").write_text(json.dumps(q))
    with pytest.raises(A.RunValidationError, match="duplicate query IDs"):
        _validate(root)


def test_queries_from_the_wrong_split_fail(tmp_path):
    root = write_run(tmp_path)
    mask = D.split_documents(N_DOCS)
    q = json.loads((root / "squad2" / "queries.json").read_text())
    q["doc_idx"][0] = int(np.flatnonzero(mask)[0])  # an exploratory document in a confirmatory run
    (root / "squad2" / "queries.json").write_text(json.dumps(q))
    with pytest.raises(A.RunValidationError, match="outside the confirmatory split"):
        _validate(root)


def test_incompatible_axis_order_fails(tmp_path):
    root = write_run(tmp_path)
    m = json.loads((root / "covidqa" / "manifest.json").read_text())
    m["config"]["retrievers"] = list(reversed(m["config"]["retrievers"]))
    m["config_sha256"] = hashlib.sha256(json.dumps(m["config"], sort_keys=True).encode()).hexdigest()
    (root / "covidqa" / "manifest.json").write_text(json.dumps(m))
    with pytest.raises(A.RunValidationError, match="incompatible axes"):
        _validate(root)


@pytest.mark.parametrize("mutation, message", [
    (lambda z: {**z, "scores": z["scores"][:, :-1]}, "scores shape"),
    (lambda z: {**z, "scores": np.where(np.ones_like(z["scores"], bool), np.nan, z["scores"]).astype(np.float16)}, "non-finite"),
    (lambda z: {**z, "scores": (z["scores"] + 2).astype(np.float16)}, r"outside \[0, 1\]"),
    (lambda z: {k: v for k, v in z.items() if k != "scores"}, "required member 'scores'"),
    (lambda z: {**z, "words": (z["words"] + 5000).astype(np.int32)}, "more than"),
])
def test_bad_npz_arrays_fail(tmp_path, mutation, message):
    root = write_run(tmp_path)
    path = root / "squad2" / "fixed-128.npz"
    with np.load(path) as z:
        arrays = {k: z[k] for k in z.files}
    np.savez_compressed(path, **mutation(arrays))
    with pytest.raises(A.RunValidationError, match=message):
        _validate(root)


def test_missing_chunking_fails(tmp_path):
    root = write_run(tmp_path, chunkings=[c for c in (s.name for s in default_specs()) if c != "paragraph-256"])
    with pytest.raises(A.RunValidationError, match="paragraph-256"):
        _validate(root, "SMOKE")


def test_operating_point_indices_come_from_manifest_labels():
    ops = ["B2048", "k1", "B512", "k5"]
    assert A.op_indices("count", 512, ops=ops) == [1, 3]
    assert A.op_indices("budget", 512, ops=ops) == [0, 2]
    assert A.op_indices("budget", 1024, ops=ops) == [0]
    with pytest.raises(A.RunValidationError):
        A.parse_ops(["top5"])


def test_study1b_run_validates_and_rejects_study1_run(tmp_path):
    root = write_run(tmp_path / "b", study="1b", chunkings=list(A1b.CHUNKINGS), retrievers=list(A1b.RETRIEVERS))
    assert _validate(root, study="1b")["study"] == "1b"
    with pytest.raises(A.RunValidationError, match="study mismatch"):
        _validate(write_run(tmp_path / "a"), study="1b")


def test_cli_rejects_nonpositive_resampling_counts_and_bad_runs(tmp_path, capsys):
    with pytest.raises(SystemExit):
        A.main(["--run", str(tmp_path), "--out", str(tmp_path / "o"), "--label", "SMOKE", "--reps", "0"])
    assert "positive integer" in capsys.readouterr().err
    root = write_run(tmp_path / "run", datasets=("squad2",))
    assert A.main(["--run", str(root), "--out", str(tmp_path / "o"), "--label", "CONFIRMATORY"]) == 2
    assert not (tmp_path / "o").exists()  # nothing written for an invalid analysis


def test_smoke_analysis_end_to_end_is_labelled(tmp_path):
    root = write_run(tmp_path / "run", datasets=("squad2", "covidqa"))
    out = tmp_path / "o"
    assert A.main(["--run", str(root), "--out", str(out), "--label", "SMOKE", "--reps", "50", "--joint-reps", "20"]) == 0
    res = json.loads((out / "results.json").read_text())
    md = (out / "results.md").read_text()
    assert res["label"] == "SMOKE" and "SMOKE / PARTIAL ANALYSIS" in md
    assert res["analysis_settings"]["verdict_bootstrap_resamples"] == 50 and "50 paired percentile-bootstrap" in md
    assert "git" not in json.dumps(res["source_manifests"])


def test_existing_output_directory_is_not_overwritten(tmp_path):
    root = write_run(tmp_path / "run", datasets=("squad2",))
    out = tmp_path / "o"
    out.mkdir()
    (out / "results.json").write_text("{}")
    with pytest.raises(SystemExit, match="already contains files"):
        A.main(["--run", str(root), "--out", str(out), "--label", "SMOKE", "--reps", "10", "--joint-reps", "5"])
    assert (out / "results.json").read_text() == "{}"


def test_analyze1b_cli_end_to_end_and_markdown_settings(tmp_path):
    root = write_run(tmp_path / "run", datasets=("squad2", "cuad"), study="1b", chunkings=list(A1b.CHUNKINGS),
                     retrievers=list(A1b.RETRIEVERS))
    out = tmp_path / "o"
    assert A1b.main(["--run", str(root), "--out", str(out), "--label", "SMOKE", "--reps", "40", "--joint-reps", "10"]) == 0
    res = json.loads((out / "results.json").read_text())
    md = (out / "results.md").read_text()
    assert set(res) >= {"H4", "H4b", "H5", "H5b", "H4_sensitivity", "semantic_wins", "analysis_settings"}
    assert "40 paired percentile-bootstrap" in md and "SMOKE / PARTIAL" in md
    for h in ("H4", "H4b", "H5", "H5b"):  # JSON and Markdown agree
        assert f"{100 * res[h]['estimate']:.1f}%" in md
    assert A1b.main(["--run", str(root), "--out", str(tmp_path / "o2"), "--label", "CONFIRMATORY"]) == 2
