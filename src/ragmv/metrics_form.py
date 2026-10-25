"""Metrics-only form of the answer-generation logs, for a release that carries no answer or response text.

Each generation log segment `X.jsonl` (`generations.jsonl`, `generations.seg-NNN.jsonl`) becomes `X.metrics.jsonl`,
line for line and in the same order, so every count the analysis reports (lines, accepted, superseded rows) is
unchanged. A row keeps exactly the fields in KEEP. `response_unanswerable` is derived from the response with the rule
the analysis uses. The fields in DROP are removed:

  answers   gold answer strings copied from the dataset
  response  the model's answer, which often reproduces wording of the retrieved passages
  prompt    the assembled prompt (contains the retrieved passages; the stored logs do not keep it)

Any field outside KEEP and DROP stops the conversion: a new field has to be reviewed before it can be released.
Identifiers that remain (`qid`, `job_id`) are the datasets' own question IDs; CUAD's embed the contract's EDGAR file
name and the clause category. See docs/remediation/RIGHTS_AND_ATTRIBUTION.md.
"""
from __future__ import annotations

import json
from pathlib import Path

SUFFIX = ".metrics.jsonl"
NUM = (int, float)
KEEP = {
    "job_id": str, "qid": str, "chunking": str, "op": str, "status": str, "context_words": int,
    "retrieval": dict, "em": NUM, "f1": NUM, "latency_s": NUM, "model": str, "model_version": str,
    "finish_reason": str, "usage": dict, "called_utc": str, "prompt_sha256": str, "hardware": str,
}
OPTIONAL = {"hardware", "latency_s", "finish_reason", "model_version"}
RETRIEVAL = ("hit_strict", "hit_lenient", "coverage")
USAGE = {"prompt_token_count", "candidates_token_count", "thoughts_token_count", "total_token_count",
         "prompt_tokens_details"}
DERIVED = "response_unanswerable"
DROP = ("answers", "response", "prompt")


class MetricsFormError(ValueError):
    """A row cannot be converted or does not conform to the metrics-only schema."""


def unanswerable(response) -> bool | None:
    """The analysis rule: the response, stripped and lower-cased, starts with "unanswerable"."""
    return response.strip().lower().startswith("unanswerable") if isinstance(response, str) else None


def _check_usage(usage: dict, where: str) -> None:
    for k, v in usage.items():
        if k not in USAGE:
            raise MetricsFormError(f"{where}: usage field {k!r} is not in the reviewed schema")
        if k == "prompt_tokens_details":
            if not (isinstance(v, list) and all(isinstance(x, dict) and set(x) <= {"modality", "token_count"}
                                                and isinstance(x.get("token_count", 0), int) for x in v)):
                raise MetricsFormError(f"{where}: usage.prompt_tokens_details has an unreviewed shape")
        elif not isinstance(v, int) or isinstance(v, bool):
            raise MetricsFormError(f"{where}: usage.{k} is not an integer")


def check_row(row: dict, where: str = "row") -> None:
    """Raise unless `row` is exactly a metrics-only row."""
    if not isinstance(row, dict):
        raise MetricsFormError(f"{where}: not a JSON object")
    extra = set(row) - set(KEEP) - {DERIVED}
    if extra:
        raise MetricsFormError(f"{where}: fields outside the metrics-only schema: {sorted(extra)}")
    missing = set(KEEP) - OPTIONAL - set(row)
    if missing or DERIVED not in row:
        raise MetricsFormError(f"{where}: missing fields {sorted(missing | ({DERIVED} - set(row)))}")
    for k, t in KEEP.items():
        if k in row and row[k] is not None and (not isinstance(row[k], t) or isinstance(row[k], bool)):
            raise MetricsFormError(f"{where}: {k} has type {type(row[k]).__name__}")
    if set(row["retrieval"]) != set(RETRIEVAL) or not all(isinstance(row["retrieval"][k], NUM) for k in RETRIEVAL):
        raise MetricsFormError(f"{where}: retrieval must hold exactly {RETRIEVAL} as numbers")
    _check_usage(row["usage"], where)
    if row[DERIVED] is not None and not isinstance(row[DERIVED], bool):
        raise MetricsFormError(f"{where}: {DERIVED} must be true, false or null")


def to_metrics(row: dict, where: str = "row") -> dict:
    """The metrics-only form of one log row; refuses rows with fields that have not been reviewed."""
    unknown = set(row) - set(KEEP) - set(DROP)
    if unknown:
        raise MetricsFormError(f"{where}: unreviewed fields {sorted(unknown)}; review them before release")
    out = {k: row[k] for k in KEEP if k in row}
    out[DERIVED] = unanswerable(row.get("response"))
    check_row(out, where)
    return out


def metrics_name(log_name: str) -> str:
    if not log_name.endswith(".jsonl") or log_name.endswith(SUFFIX):
        raise MetricsFormError(f"{log_name}: not a generation log name")
    return log_name[: -len(".jsonl")] + SUFFIX


def source_name(metrics_file: str) -> str:
    """Name of the log segment a metrics file was derived from."""
    if not metrics_file.endswith(SUFFIX):
        raise MetricsFormError(f"{metrics_file}: not a metrics-only file")
    return metrics_file[: -len(SUFFIX)] + ".jsonl"


def metrics_paths(ds_dir: Path) -> list[Path]:
    """generations.metrics.jsonl followed by generations.seg-NNN.metrics.jsonl, in order."""
    first = Path(ds_dir) / ("generations" + SUFFIX)
    segs = sorted(Path(ds_dir).glob("generations.seg-[0-9][0-9][0-9]" + SUFFIX))
    return ([first] if first.exists() else []) + segs


def convert_log(src: Path) -> str:
    """Text of the metrics-only form of one log segment. The source must be complete (every line a JSON object and a
    final newline): an interrupted log is not released."""
    text = Path(src).read_text(encoding="utf-8")
    if text and not text.endswith("\n"):
        raise MetricsFormError(f"{src}: incomplete final record; not converted")
    lines = []
    for i, line in enumerate(text.splitlines(), 1):
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise MetricsFormError(f"{src}:{i}: malformed JSON ({exc})") from exc
        lines.append(json.dumps(to_metrics(row, f"{src}:{i}"), ensure_ascii=False))
    return "".join(x + "\n" for x in lines)
