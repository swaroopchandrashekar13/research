"""Run validation keeps every array diagnostic, checks every query identifier, and applies the provenance policy."""
import hashlib
import json

import numpy as np
import pytest
from test_run_validation import CHUNKS1, N_Q, _validate, write_run

from ragmv import analyze as A
from ragmv import provenance as PV


def _rewrite_npz(path, change):
    with np.load(path) as z:
        arrays = {k: z[k] for k in z.files}
    np.savez_compressed(path, **change(arrays))


def _drop(*members):
    return lambda z: {k: v for k, v in z.items() if k not in members}


def _edit_queries(root, dataset, change):
    p = root / dataset / "queries.json"
    q = json.loads(p.read_text())
    change(q)
    p.write_text(json.dumps(q))


def _edit_manifest(root, dataset, change, refingerprint=True):
    p = root / dataset / "manifest.json"
    m = json.loads(p.read_text())
    change(m)
    if refingerprint:
        m["config_sha256"] = hashlib.sha256(json.dumps(m["config"], sort_keys=True).encode()).hexdigest()
    p.write_text(json.dumps(m))


# ------------------------------------------------------------------------------------- array diagnostics (PY-001)
@pytest.mark.parametrize("members, expect", [
    (("words",), ["['words']"]),
    (("rr10",), ["['rr10']"]),
    (("words", "rr10"), ["['words', 'rr10']"]),
])
def test_missing_optional_members_are_reported(tmp_path, members, expect):
    root = write_run(tmp_path)
    _rewrite_npz(root / "cuad" / "fixed-512.npz", _drop(*members))
    v = _validate(root)
    notes = [x for x in v["legacy_limitations"] if "cuad/fixed-512.npz" in x]
    assert len(notes) == 1 and all(e in notes[0] for e in expect)


def test_missing_scores_is_an_error(tmp_path):
    root = write_run(tmp_path)
    _rewrite_npz(root / "cuad" / "fixed-512.npz", _drop("scores"))
    with pytest.raises(A.RunValidationError, match="required member 'scores'"):
        _validate(root)


def test_malformed_words_array_is_an_error(tmp_path):
    root = write_run(tmp_path)
    _rewrite_npz(root / "covidqa" / "fixed-128.npz", lambda z: {**z, "words": z["words"].astype(np.float32)})
    with pytest.raises(A.RunValidationError, match="words array"):
        _validate(root)


def test_complete_legacy_run_has_no_array_notes(tmp_path):
    v = _validate(write_run(tmp_path))
    assert not [x for x in v["legacy_limitations"] if ".npz" in x]


def test_scores_loaded_before_validation_keep_their_notes(tmp_path):
    root = write_run(tmp_path)
    _rewrite_npz(root / "squad2" / "fixed-128.npz", _drop("rr10"))
    run = A.Run(root)
    run.scores("squad2", "fixed-128")  # cached before validate()
    v = run.validate("CONFIRMATORY", CHUNKS1, A.full_design_study1())
    assert any("squad2/fixed-128.npz" in x and "rr10" in x for x in v["legacy_limitations"])
    assert v["legacy_limitations"] == run.legacy


def test_repeated_validation_is_deterministic_without_duplicates(tmp_path):
    root = write_run(tmp_path)
    _rewrite_npz(root / "squad2" / "fixed-128.npz", _drop("words"))
    run = A.Run(root)
    first = run.validate("CONFIRMATORY", CHUNKS1, A.full_design_study1())["legacy_limitations"]
    second = run.validate("CONFIRMATORY", CHUNKS1, A.full_design_study1())["legacy_limitations"]
    assert first == second == run.legacy and len(first) == len(set(first))
    assert sum("squad2/fixed-128.npz" in x for x in second) == 1


def test_different_missing_members_in_several_chunkings(tmp_path):
    root = write_run(tmp_path)
    _rewrite_npz(root / "cuad" / "fixed-128.npz", _drop("words"))
    _rewrite_npz(root / "qasper" / "paragraph-256.npz", _drop("rr10"))
    notes = _validate(root)["legacy_limitations"]
    assert any("cuad/fixed-128.npz" in x and "words" in x for x in notes)
    assert any("qasper/paragraph-256.npz" in x and "rr10" in x for x in notes)


def test_json_and_markdown_report_the_same_warnings(tmp_path):
    root = write_run(tmp_path / "run", datasets=("squad2", "covidqa"))
    _rewrite_npz(root / "squad2" / "fixed-512.npz", _drop("words"))
    out = tmp_path / "o"
    assert A.main(["--run", str(root), "--out", str(out), "--label", "SMOKE", "--reps", "20", "--joint-reps", "5"]) == 0
    res = json.loads((out / "results.json").read_text())
    md = (out / "results.md").read_text()
    notes = res["validation"]["legacy_limitations"]
    assert any("squad2/fixed-512.npz" in x for x in notes)
    assert all(f"- {x}" in md for x in notes)


# ------------------------------------------------------------------------------- strict schema for new runs (PY-001)
def _strict_run(tmp_path, drop=()):
    root = write_run(tmp_path)
    for d in ("squad2", "covidqa", "cuad", "qasper"):
        _edit_manifest(root, d, lambda m: (m.update(schema="ragmv.run/2", code_sha256="0" * 64,
                                                    inputs_sha256={"x": "0" * 64}), m["config"].update(study="1")))
        for p in (root / d).glob("*.npz"):
            def add(z):
                shape = z["words"].shape[:2]
                z.update(depth=np.full(shape, 50, np.int32), expansions=np.zeros(shape, np.int16),
                         exhausted=np.zeros(shape, bool))
                return {k: v for k, v in z.items() if k not in drop}
            _rewrite_npz(p, add)
    return root


def test_strict_new_run_validates_when_complete(tmp_path):
    v = _validate(_strict_run(tmp_path))
    assert not [x for x in v["legacy_limitations"] if ".npz" in x]
    assert v["provenance"]["status"] == "complete"


@pytest.mark.parametrize("member", ["rr10", "words", "depth", "exhausted"])
def test_strict_new_run_rejects_missing_evidence(tmp_path, member):
    with pytest.raises(A.RunValidationError, match=f"'{member}'"):
        _validate(_strict_run(tmp_path, drop=(member,)))


def test_strict_new_run_accepts_underfill_only_with_exhaustion(tmp_path):
    root = _strict_run(tmp_path)
    _rewrite_npz(root / "squad2" / "fixed-128.npz", lambda z: {**z, "words": (z["words"] // 2).astype(np.int32),
                                                               "exhausted": np.ones_like(z["exhausted"])})
    assert _validate(root)["provenance"]["status"] == "complete"


def test_strict_new_run_rejects_unexplained_underfill(tmp_path):
    root = _strict_run(tmp_path)
    _rewrite_npz(root / "squad2" / "fixed-128.npz", lambda z: {**z, "words": (z["words"] // 2).astype(np.int32)})
    with pytest.raises(A.RunValidationError, match="below its budget"):
        _validate(root)


# --------------------------------------------------------------------------------------- query identifiers (PY-002)
@pytest.mark.parametrize("positions", [[0], [N_Q // 2], [N_Q - 1], [1, 7, 20]])
def test_every_query_id_prefix_is_checked(tmp_path, positions):
    root = write_run(tmp_path)

    def bad(q):
        for i in positions:
            q["qids"][i] = f"cuad:x{i}"
    _edit_queries(root, "squad2", bad)
    with pytest.raises(A.RunValidationError, match="not prefixed") as exc:
        _validate(root)
    assert f"{len(positions)} query ID" in str(exc.value) and str(positions[0]) in str(exc.value)


@pytest.mark.parametrize("value, message", [(17, "not a string"), ("", "empty"), ("squad2:", "empty"),
                                            (None, "not a string")])
def test_non_string_or_empty_query_ids_fail(tmp_path, value, message):
    root = write_run(tmp_path)
    _edit_queries(root, "squad2", lambda q: q["qids"].__setitem__(3, value))
    with pytest.raises(A.RunValidationError, match=message):
        _validate(root)


def test_duplicate_ids_are_named(tmp_path):
    root = write_run(tmp_path)
    _edit_queries(root, "covidqa", lambda q: q["qids"].__setitem__(5, q["qids"][2]))
    with pytest.raises(A.RunValidationError, match="covidqa:q2"):
        _validate(root)


def test_empty_query_collection_fails(tmp_path):
    root = write_run(tmp_path)
    _edit_queries(root, "cuad", lambda q: q.update(qids=[], doc_idx=[]))
    _edit_manifest(root, "cuad", lambda m: m.update(n_queries=0), refingerprint=False)
    with pytest.raises(A.RunValidationError, match="no queries"):
        _validate(root)


def test_query_and_document_lengths_must_match(tmp_path):
    root = write_run(tmp_path)
    _edit_queries(root, "qasper", lambda q: q["doc_idx"].pop())
    with pytest.raises(A.RunValidationError, match="doc_idx"):
        _validate(root)


@pytest.mark.parametrize("value, message", [(1.5, "integers"), ("3", "integers"), (-1, "outside"), (10_000, "outside"),
                                            (True, "integers")])
def test_document_indices_must_be_integers_in_range(tmp_path, value, message):
    root = write_run(tmp_path)
    _edit_queries(root, "cuad", lambda q: q["doc_idx"].__setitem__(4, value))
    with pytest.raises(A.RunValidationError, match=message):
        _validate(root)


def test_valid_query_input_passes(tmp_path):
    assert _validate(write_run(tmp_path))["datasets"] == ["squad2", "covidqa", "cuad", "qasper"]


def test_invalid_queries_stop_before_any_output(tmp_path):
    root = write_run(tmp_path / "run", datasets=("squad2",))
    _edit_queries(root, "squad2", lambda q: q["qids"].__setitem__(10, "cuad:z"))
    out = tmp_path / "o"
    assert A.main(["--run", str(root), "--out", str(out), "--label", "SMOKE"]) == 2
    assert not out.exists()


@pytest.mark.parametrize("content, message", [("{not json", "not valid JSON"), ("[]", "JSON object"),
                                              ('{"status": "ok"}', "config")])
def test_malformed_manifest_is_a_validation_error(tmp_path, content, message):
    root = write_run(tmp_path, datasets=("squad2",))
    (root / "squad2" / "manifest.json").write_text(content)
    with pytest.raises(A.RunValidationError, match=message):
        A.Run(root)


def test_malformed_queries_file_is_a_validation_error(tmp_path):
    root = write_run(tmp_path, datasets=("squad2",))
    (root / "squad2" / "queries.json").write_text('{"qids": "abc", "doc_idx": []}')
    with pytest.raises(A.RunValidationError, match="qids"):
        A.Run(root)


# ------------------------------------------------------------------------------------- provenance policy (HASH-001)
def _historical_copy(tmp_path, key="experiments/E1_retrieval_multiverse/runs/confirmatory-20261018", start=None):
    root = write_run(tmp_path / key)
    for d in ("squad2", "covidqa", "cuad", "qasper"):
        stamp = start or PV.HISTORICAL_RUNS[key][d]
        _edit_manifest(root, d, lambda m: m.update(config_sha256=PV.DIGEST_REMOVED, started_utc=stamp),
                       refingerprint=False)
    return root


def test_removed_digest_is_accepted_only_for_registered_historical_records(tmp_path):
    v = _validate(_historical_copy(tmp_path))
    assert v["provenance"]["status"] == "incomplete"
    assert any("configuration fingerprint cannot be checked" in x for x in v["provenance"]["notes"])


def test_removed_digest_in_an_unregistered_run_fails(tmp_path):
    root = write_run(tmp_path)
    _edit_manifest(root, "cuad", lambda m: m.update(config_sha256=PV.DIGEST_REMOVED), refingerprint=False)
    with pytest.raises(A.RunValidationError, match="not a registered historical record"):
        _validate(root)


def test_registered_name_with_a_different_record_fails(tmp_path):
    with pytest.raises(A.RunValidationError, match="not a registered historical record"):
        _validate(_historical_copy(tmp_path, start="2030-01-01T00:00:00+00:00"))


@pytest.mark.parametrize("value", ["redacted: something else", "abc", "0" * 63])
def test_other_markers_or_malformed_digests_fail(tmp_path, value):
    root = write_run(tmp_path)
    _edit_manifest(root, "cuad", lambda m: m.update(config_sha256=value), refingerprint=False)
    with pytest.raises(A.RunValidationError, match="config_sha256"):
        _validate(root)


def test_new_runs_with_verified_fingerprints_have_complete_provenance_fields(tmp_path):
    v = _validate(write_run(tmp_path))
    assert v["provenance"]["status"] in ("complete", "incomplete")
    assert not any("fingerprint cannot be checked" in x for x in v["provenance"]["notes"])
