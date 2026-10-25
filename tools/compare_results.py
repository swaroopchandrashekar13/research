"""Field-level comparison of two results.json files (a committed baseline and a recomputation).

Tolerances are fixed in advance and printed with the report: integers, strings, booleans and verdict labels must be
identical; floats may differ by at most --float-atol (default 1e-12, i.e. bit-for-bit up to JSON round-off). Every
difference is listed, including tiny ones. Failures (exit 1):

- a scientific value differs beyond tolerance, or changes type (number vs string, bool vs number);
- a scientific field of the baseline is missing from the recomputation;
- a scientific value is NaN or infinite in either file;
- with --inputs-against, a file the recomputation consumed does not have the digest the protected list records.

Only the metadata fields in METADATA (code and input identities, validation notes, source-manifest echoes) may differ
or exist in one file only; fields that exist only in the recomputation are listed (new outputs) but cannot hide a
change, because every baseline field must be present and equal.

Usage: python -I tools/compare_results.py OLD.json NEW.json [--float-atol 1e-12]
           [--inputs-against docs/remediation/PROTECTED_SHA256.txt --run-dir RUN]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METADATA = ("analysis_code_sha256", "analysis_run_dir", "consumed_inputs_sha256", "code_sha256", "validation",
            "source_manifests")


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def is_metadata(key: str, extra: tuple[str, ...] = ()) -> bool:
    return any(key == m or key.startswith((m + ".", m + "[")) for m in METADATA + tuple(extra))


def _nonfinite(v) -> bool:
    return isinstance(v, float) and not math.isfinite(v)


def compare(old: dict, new: dict, atol: float = 1e-12, ignore: tuple[str, ...] = ()) -> dict:
    """`ignore` may only name metadata prefixes (see METADATA); anything else raises ValueError."""
    bad = [p for p in ignore if not is_metadata(p) and p not in ("analysis_",)]
    if bad:
        raise ValueError(f"refusing to ignore scientific fields {bad}; only metadata {METADATA} may be ignored")
    extra = tuple(p for p in ignore if p == "analysis_")
    a, b = dict(flatten(old)), dict(flatten(new))
    out = {"identical": 0, "within_tolerance": [], "different": [], "verdict_changes": [], "nonfinite": [],
           "missing_scientific": [], "only_old_metadata": [], "only_new": sorted(set(b) - set(a)),
           "metadata_differences": []}
    for k in sorted(set(a) - set(b)):
        (out["only_old_metadata"] if is_metadata(k, extra) else out["missing_scientific"]).append(k)
    for k in sorted(set(a) & set(b)):
        x, y = a[k], b[k]
        meta = is_metadata(k, extra)
        if not meta and (_nonfinite(x) or _nonfinite(y)):
            out["nonfinite"].append((k, x, y))
            continue
        if x == y and type(x) is type(y):
            out["identical"] += 1
        elif meta:
            out["metadata_differences"].append((k, x, y))
        elif isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) \
                and not isinstance(y, bool) and (isinstance(x, float) or isinstance(y, float)):
            d = abs(float(x) - float(y))
            (out["within_tolerance"] if d <= atol else out["different"]).append((k, x, y, d))
        else:
            out["different"].append((k, x, y, None))
            if k.endswith("verdict"):
                out["verdict_changes"].append((k, x, y))
    for k in out["only_new"]:
        if not is_metadata(k, extra) and _nonfinite(b[k]):
            out["nonfinite"].append((k, None, b[k]))
    return out


def failed(res: dict) -> bool:
    return bool(res["different"] or res["missing_scientific"] or res["nonfinite"] or res.get("input_mismatches"))


def check_inputs(new: dict, protected: Path, run_dir: Path) -> list[str]:
    """Consumed inputs of the recomputation whose digest differs from the protected list (or is not listed)."""
    listed = {}
    for line in protected.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            digest, rel = line.split(None, 1)
            listed[rel.strip()] = digest
    base = Path(run_dir).resolve().relative_to(ROOT) if Path(run_dir).resolve().is_relative_to(ROOT) else Path(run_dir)
    bad = []
    for rel, digest in (new.get("consumed_inputs_sha256") or {}).items():
        key = str(base / rel)
        if listed.get(key) != digest:
            bad.append(f"{key}: {'not in the protected list' if key not in listed else 'digest differs'}")
    if not new.get("consumed_inputs_sha256"):
        bad.append("the recomputation records no consumed inputs")
    return bad


def report(res: dict, atol: float) -> str:
    lines = [f"tolerance: floats |Δ| <= {atol:g}; everything else exact; metadata fields: {', '.join(METADATA)}",
             f"identical fields: {res['identical']}", f"within tolerance (non-zero Δ): {len(res['within_tolerance'])}",
             f"different: {len(res['different'])}", f"verdict changes: {len(res['verdict_changes'])}",
             f"missing scientific fields: {len(res['missing_scientific'])}", f"non-finite values: {len(res['nonfinite'])}",
             f"metadata differences: {len(res['metadata_differences'])}",
             f"only in old (metadata): {len(res['only_old_metadata'])}", f"only in new: {len(res['only_new'])}"]
    if "input_mismatches" in res:
        lines.append(f"consumed-input digest mismatches: {len(res['input_mismatches'])}")
    for k, x, y, d in res["within_tolerance"]:
        lines.append(f"  ~ {k}: {x!r} -> {y!r} (|Δ|={d:.3g})")
    for k, x, y, d in res["different"]:
        lines.append(f"  ! {k}: {x!r} -> {y!r}" + (f" (|Δ|={d:.3g})" if d is not None else ""))
    for k in res["missing_scientific"]:
        lines.append(f"  ! missing in new: {k}")
    for k, x, y in res["nonfinite"]:
        lines.append(f"  ! non-finite: {k}: {x!r} -> {y!r}")
    for x in res.get("input_mismatches", []):
        lines.append(f"  ! input: {x}")
    for k, x, y in res["metadata_differences"]:
        lines.append(f"  m {k}: {str(x)[:40]!r} -> {str(y)[:40]!r}")
    for k in res["only_old_metadata"]:
        lines.append(f"  - {k}")
    for k in res["only_new"]:
        lines.append(f"  + {k}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--float-atol", type=float, default=1e-12)
    ap.add_argument("--inputs-against", type=Path, help="protected digest list the consumed inputs must match")
    ap.add_argument("--run-dir", type=Path, help="run directory the recomputation consumed (with --inputs-against)")
    args = ap.parse_args(argv)
    if args.float_atol < 0 or args.float_atol > 1e-9:
        ap.error("--float-atol must be between 0 and 1e-9 (results are recomputed exactly; no tolerance inflation)")
    new = json.loads(Path(args.new).read_text())
    res = compare(json.loads(Path(args.old).read_text()), new, args.float_atol)
    if args.inputs_against:
        if not args.run_dir:
            ap.error("--inputs-against needs --run-dir")
        res["input_mismatches"] = check_inputs(new, args.inputs_against, args.run_dir)
    print(report(res, args.float_atol))
    return 1 if failed(res) else 0


if __name__ == "__main__":
    sys.exit(main())
