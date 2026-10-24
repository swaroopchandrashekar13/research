"""Field-level comparison of two results.json files (or any two JSON documents).

Tolerances are fixed in advance and printed with the report: integers, strings, booleans and verdict labels must be
identical; floats may differ by at most --float-atol (default 1e-12, i.e. bit-for-bit up to JSON round-off). Every
difference is listed, including tiny ones, and fields that exist in only one file are listed separately (new
metadata such as `analysis_settings` is expected there). A changed verdict string is always reported as a failure,
whatever the tolerance.

Usage: python -I tools/compare_results.py OLD.json NEW.json [--float-atol 1e-12] [--ignore source_manifests ...]
Exit code: 0 if no value differs beyond tolerance (added/removed fields alone do not fail), 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import math
import sys


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def compare(old: dict, new: dict, atol: float = 1e-12, ignore: tuple[str, ...] = ()) -> dict:
    a = {k: v for k, v in flatten(old) if not k.startswith(ignore)}
    b = {k: v for k, v in flatten(new) if not k.startswith(ignore)}
    out = {"identical": 0, "within_tolerance": [], "different": [], "only_old": sorted(set(a) - set(b)),
           "only_new": sorted(set(b) - set(a)), "verdict_changes": []}
    for k in sorted(set(a) & set(b)):
        x, y = a[k], b[k]
        if x == y and type(x) is type(y):
            out["identical"] += 1
        elif isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool) \
                and not isinstance(y, bool) and (isinstance(x, float) or isinstance(y, float)):
            d = abs(float(x) - float(y))
            (out["within_tolerance"] if d <= atol or (math.isnan(x) and math.isnan(y)) else out["different"]).append(
                (k, x, y, d))
        else:
            out["different"].append((k, x, y, None))
            if k.endswith("verdict"):
                out["verdict_changes"].append((k, x, y))
    return out


def report(res: dict, atol: float) -> str:
    lines = [f"tolerance: floats |Δ| <= {atol:g}; everything else exact",
             f"identical fields: {res['identical']}", f"within tolerance (non-zero Δ): {len(res['within_tolerance'])}",
             f"different: {len(res['different'])}", f"verdict changes: {len(res['verdict_changes'])}",
             f"only in old: {len(res['only_old'])}", f"only in new: {len(res['only_new'])}"]
    for k, x, y, d in res["within_tolerance"]:
        lines.append(f"  ~ {k}: {x!r} -> {y!r} (|Δ|={d:.3g})")
    for k, x, y, d in res["different"]:
        lines.append(f"  ! {k}: {x!r} -> {y!r}" + (f" (|Δ|={d:.3g})" if d is not None else ""))
    for k in res["only_old"]:
        lines.append(f"  - {k}")
    for k in res["only_new"]:
        lines.append(f"  + {k}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--float-atol", type=float, default=1e-12)
    ap.add_argument("--ignore", nargs="*", default=[])
    args = ap.parse_args(argv)
    res = compare(json.load(open(args.old)), json.load(open(args.new)), args.float_atol, tuple(args.ignore))
    print(report(res, args.float_atol))
    return 1 if res["different"] else 0


if __name__ == "__main__":
    sys.exit(main())
