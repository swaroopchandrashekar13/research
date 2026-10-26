"""POST-HOC bound on the effect of underfilled budget selections (plan: docs/remediation/POSTHOC_PLAN_underfill_bound.md).

Reads the census (tools/budget_underfill_census.py), copies each affected stored run into WORK (keeping its
experiments/<study>/runs/<id> path, so the historical-record binding still applies), sets the affected cells' three
metrics to 1.0 (the upper bound: adding retrieved text can never lower these metrics; the lower bound is the stored
run), re-runs the planned analysis with its planned settings and compares every field with the stored results.
The stored runs are only read.

Usage: python -I tools/underfill_bound.py --census CENSUS.json --work NEW_DIR --out-json FILE
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from compare_results import compare  # noqa: E402

ANALYSES = {"confirmatory-kaggle-gpu": ("E3_semantic_dense", "ragmv.analyze1b", "CONFIRMATORY"),
            "exploratory-kaggle-gpu": ("E3_semantic_dense", "ragmv.analyze1b", "EXPLORATORY"),
            "confirmatory-20261018": ("E1_retrieval_multiverse", "ragmv.analyze", "CONFIRMATORY"),
            "pilot-exploratory-20261018": ("E1_retrieval_multiverse", "ragmv.analyze", "EXPLORATORY")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True, type=Path)
    ap.add_argument("--work", required=True, type=Path)
    ap.add_argument("--out-json", required=True, type=Path)
    args = ap.parse_args(argv)
    if args.work.exists() and any(args.work.iterdir()):
        raise SystemExit(f"{args.work} is not empty")
    cells = json.loads(args.census.read_text())["underfilled"]
    report = {"label": "POST-HOC upper bound for underfilled budget selections", "cells": cells, "runs": {}}
    for run_id in sorted({c["run"] for c in cells}):
        exp, module, label = ANALYSES[run_id]
        src = ROOT / "experiments" / exp / "runs" / run_id
        dst = args.work / "experiments" / exp / "runs" / run_id
        shutil.copytree(src, dst)
        for c in [c for c in cells if c["run"] == run_id]:
            m = json.loads((dst / c["dataset"] / "manifest.json").read_text())
            r, j = m["config"]["retrievers"].index(c["retriever"]), m["config"]["ops"].index(f"B{c['budget']}")
            path = dst / c["dataset"] / f"{c['chunking']}.npz"
            with np.load(path, allow_pickle=False) as z:
                arrays = {k: z[k] for k in z.files}
            c["stored_scores"] = arrays["scores"][r, c["query_index"], j].astype(float).tolist()
            arrays["scores"][r, c["query_index"], j] = 1.0
            np.savez_compressed(path, **arrays)
        out = args.work / "analysis" / run_id
        proc = subprocess.run([sys.executable, "-I", "-c", "import sys, runpy; sys.path.insert(0, sys.argv[1]); "
                               "sys.argv = [sys.argv[2]] + sys.argv[3:]; runpy.run_module(sys.argv[0], run_name='__main__')",
                               str(ROOT / "src"), module, "--run", str(dst), "--label", label, "--out", str(out)],
                              capture_output=True, text=True)
        if proc.returncode:
            raise SystemExit(f"analysis failed: {proc.stderr[-800:]}")
        stored = json.loads((ROOT / "experiments" / exp / "analysis" / run_id / "results.json").read_text())
        upper = json.loads((out / "results.json").read_text())
        res = compare(stored, upper)
        verdicts = {h: (stored[h]["verdict"], upper[h]["verdict"]) for h in stored if isinstance(stored[h], dict)
                    and "verdict" in stored[h]}
        report["runs"][run_id] = {
            "changed_fields": [{"field": k, "stored": x, "upper_bound": y} for k, x, y, _ in res["different"]],
            "identical_fields": res["identical"], "hypothesis_verdicts": verdicts,
            "verdict_changes": [h for h, (a, b) in verdicts.items() if a != b]}
    args.out_json.write_text(json.dumps(report, indent=2))
    for run_id, r in report["runs"].items():
        print(f"{run_id}: {len(r['changed_fields'])} fields changed at the upper bound; verdict changes: {r['verdict_changes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
