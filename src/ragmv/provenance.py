"""Provenance policy for stored runs: which historical runs may carry removed-value markers, and what that means.

The owner removed machine-readable identities (configuration digests, prompt digests, model revisions, model-file and
upload-archive digests) from the original runs. Those values are not recovered. This module is the single place that
says where such markers are allowed:

- Only the runs listed in HISTORICAL_RUNS, and only the manifests whose dataset and `started_utc` are listed for that
  run, may contain the exact markers below. The binding is by run directory name (the last four path components, so a
  faithful copy of the repository validates the same way) and by each manifest's recorded start time, so a marker in
  another run, or in a different manifest under a historical run's name, is an error.
- Anything else (new runs, post-hoc runs, test fixtures) must carry real values that can be checked.

A historical run with removed values can be structurally valid, but its provenance is reported as incomplete; it
never receives a provenance pass.
"""
from __future__ import annotations

from pathlib import Path

RUN_SCHEMA = "ragmv.run/2"  # manifests written by ragmv.run / ragmv.run1b with adaptive-depth budget filling
DIGEST_REMOVED = "redacted: historical digest removed"
GIT_REMOVED = "redacted: unresolvable historical Git commit"
REVISION_REMOVED = "@[revision removed]"
MODEL_REVISION_REMOVED = "redacted: model revision removed"
MODEL_FILE_DIGEST_REMOVED = "redacted: model file digest removed"
UPLOAD_REMOVED = "redacted: upload-archive digest removed 2026-10-25 (docs/repair/HASH_REDACTIONS.md)"

# run directory (experiments/<study>/runs/<id>) -> {dataset: started_utc of that dataset's manifest or jobs_meta}
HISTORICAL_RUNS: dict[str, dict[str, str]] = {
    "experiments/E1_retrieval_multiverse/runs/pilot-exploratory-20261018": {
        "squad2": "2026-10-18T11:35:56+00:00", "covidqa": "2026-10-18T11:36:20+00:00",
        "cuad": "2026-10-18T11:36:49+00:00", "qasper": "2026-10-18T11:37:23+00:00"},
    "experiments/E1_retrieval_multiverse/runs/confirmatory-20261018": {
        "squad2": "2026-10-18T11:45:11+00:00", "covidqa": "2026-10-18T11:46:23+00:00",
        "cuad": "2026-10-18T11:47:25+00:00", "qasper": "2026-10-18T11:48:14+00:00"},
    "experiments/E3_semantic_dense/runs/exploratory-kaggle-gpu": {
        "squad2": "2026-10-19T17:08:57+00:00", "covidqa": "2026-10-19T17:10:52+00:00",
        "cuad": "2026-10-19T17:17:22+00:00", "qasper": "2026-10-19T17:24:25+00:00"},
    "experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu": {
        "squad2": "2026-10-19T18:17:10+00:00", "covidqa": "2026-10-19T18:19:22+00:00",
        "cuad": "2026-10-19T18:26:10+00:00", "qasper": "2026-10-19T18:33:30+00:00"},
    "experiments/E2_generation/runs/gemini36flash-20261019": {
        "squad2": "2026-10-19T04:31:31Z", "covidqa": "2026-10-19T04:31:33Z",
        "cuad": "2026-10-19T04:31:33Z", "qasper": "2026-10-19T04:31:42Z"},
    "experiments/E2_generation/runs/qwen3-4b-20261019": {"squad2": "2026-10-19T07:30:40Z"},
    "experiments/E2_generation/runs/qwen3-4b-kaggle-gpu": {
        "squad2": "2026-10-19T14:37:17Z", "covidqa": "2026-10-19T14:43:53Z",
        "cuad": "2026-10-19T14:51:58Z", "qasper": "2026-10-19T15:09:33Z"},
}
UPLOAD_FILES = ("experiments/E2_generation/runs/qwen3-4b-kaggle-gpu/UPLOAD_SHA256",
                "experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu/UPLOAD_SHA256",
                "experiments/E3_semantic_dense/runs/exploratory-kaggle-gpu/UPLOAD_SHA256")


def run_key(run_dir: str | Path) -> str | None:
    """'experiments/<study>/runs/<id>' for a run directory, or None if the path does not have that shape."""
    parts = Path(run_dir).resolve().parts
    if len(parts) >= 4 and parts[-4] == "experiments" and parts[-2] == "runs":
        return "/".join(parts[-4:])
    return None


def historical_record(run_dir: str | Path, dataset: str, started_utc) -> bool:
    """True only for a registered historical run whose `dataset` record has the registered start time."""
    key = run_key(run_dir)
    return key in HISTORICAL_RUNS and HISTORICAL_RUNS[key].get(dataset) == started_utc


def is_hex_digest(value, length: int = 64) -> bool:
    return isinstance(value, str) and len(value) == length and all(c in "0123456789abcdef" for c in value)
