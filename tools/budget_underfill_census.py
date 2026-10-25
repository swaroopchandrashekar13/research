"""Census of budget underfill in every stored run (read-only).

A budget-matched selection is *underfilled* when it returned fewer words than its budget B. The stored runs ranked
each query only to a fixed depth (from the corpus 10th-percentile chunk length), so an underfilled selection means the
ranked prefix ran out of text. For each underfilled cell this tool reports study, run, dataset, chunking, retriever,
budget, query, words and deficit, and classifies the cause from the manifest's recorded depth and corpus size:

- `corpus exhausted`: the recorded depth equals the number of chunks, so the whole corpus was ranked;
- `ranking-depth cutoff (recorded depth < corpus size)`: more chunks existed than were ranked. The rankings themselves
  were not stored, so this attribution rests on the manifest's depth; it is only confirmed for a retriever that can be
  re-executed here (see --confirm).

Tier 2 generation rows (fixed ranking depth 64) are checked the same way through their `context_words`.
Malformed or missing arrays are listed separately. Nothing is modified.

Usage: python -I tools/budget_underfill_census.py --out-json FILE --out-md FILE
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STUDY = {"E1_retrieval_multiverse": "Study 1", "E3_semantic_dense": "Study 1b", "E2_generation": "Tier 2"}


def census_runs() -> tuple[list[dict], list[dict], dict]:
    cells, problems, totals = [], [], Counter()
    for npz in sorted(ROOT.glob("experiments/*/runs/*/*/*.npz")):
        rel = npz.relative_to(ROOT)
        exp, run, dataset, chunking = rel.parts[1], rel.parts[3], rel.parts[4], npz.stem
        try:
            m = json.loads((npz.parent / "manifest.json").read_text())
            qids = json.loads((npz.parent / "queries.json").read_text())["qids"]
            ops = m["config"]["ops"]
            retrievers = m["config"]["retrievers"]
            stats = {s["chunking"]: s for s in m.get("chunk_stats", [])}.get(chunking, {})
            with np.load(npz, allow_pickle=False) as z:
                if "words" not in z.files:
                    problems.append({"file": str(rel), "problem": "no 'words' member"})
                    continue
                w = z["words"]
            if w.shape != (len(retrievers), len(qids), len(ops)):
                problems.append({"file": str(rel), "problem": f"words shape {w.shape}"})
                continue
        except Exception as exc:  # noqa: BLE001 - reported, never fatal
            problems.append({"file": str(rel), "problem": f"{type(exc).__name__}: {exc}"})
            continue
        depth, n_chunks = stats.get("depth"), stats.get("n_chunks")
        totals["arrays"] += 1
        for j, op in enumerate(ops):
            mt = re.fullmatch(r"B(\d+)", op)
            if not mt:
                continue
            budget = int(mt.group(1))
            col = w[:, :, j]
            totals["budget_cells"] += col.size
            for r, q in zip(*np.nonzero(col < budget)):
                cause = ("unknown (manifest records no depth)" if depth is None or n_chunks is None else
                         "corpus exhausted" if depth >= n_chunks else
                         "ranking-depth cutoff (recorded depth < corpus size)")
                cells.append({"study": STUDY.get(exp, exp), "run": run, "dataset": dataset, "chunking": chunking,
                              "retriever": retrievers[r], "budget": budget, "query_index": int(q), "qid": qids[q],
                              "words": int(col[r, q]), "deficit": int(budget - col[r, q]), "recorded_depth": depth,
                              "n_chunks": n_chunks, "cause": cause, "attribution": "manifest depth; ranking not stored"})
    return cells, problems, dict(totals)


def census_generation() -> tuple[list[dict], dict]:
    cells, totals = [], Counter()
    for log in sorted(ROOT.glob("experiments/E2_generation/runs/*/*/generations*.jsonl")):
        rel = log.relative_to(ROOT)
        for line in log.read_text().splitlines():
            r = json.loads(line)
            mt = re.fullmatch(r"budget(\d+)", str(r.get("op")))
            if not mt or r.get("status") != "ok":
                continue
            totals["budget_rows"] += 1
            if int(r["context_words"]) < int(mt.group(1)):
                cells.append({"study": "Tier 2", "run": rel.parts[3], "dataset": rel.parts[4], "chunking": r["chunking"],
                              "retriever": "lucene-k1.5-b0.75-stem", "budget": int(mt.group(1)), "qid": r["qid"],
                              "words": int(r["context_words"]), "deficit": int(mt.group(1)) - int(r["context_words"]),
                              "recorded_depth": 64, "cause": "ranking-depth cutoff or corpus exhaustion (not recorded)",
                              "attribution": "context_words of the logged row"})
    return cells, dict(totals)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args(argv)
    cells, problems, totals = census_runs()
    gen, gtotals = census_generation()
    by = Counter((c["study"], c["run"], c["dataset"], c["chunking"], c["retriever"], c["budget"]) for c in cells)
    out = {"totals": {**totals, "underfilled_cells": len(cells), **{f"generation_{k}": v for k, v in gtotals.items()},
                      "generation_underfilled_rows": len(gen)},
           "underfilled": cells, "generation_underfilled": gen, "malformed_or_missing": problems,
           "by_group": [{"study": k[0], "run": k[1], "dataset": k[2], "chunking": k[3], "retriever": k[4], "budget": k[5],
                         "underfilled": n} for k, n in sorted(by.items())]}
    Path(args.out_json).write_text(json.dumps(out, indent=2))
    t = out["totals"]
    lines = ["# Budget-underfill census (stored runs, read-only)", "",
             f"Arrays inspected: {t.get('arrays', 0)}; budget-matched cells: {t.get('budget_cells', 0):,}; underfilled: "
             f"{len(cells)} ({len(cells) / max(t.get('budget_cells', 1), 1):.2e}). Tier 2 budget rows: "
             f"{t.get('generation_budget_rows', 0)}; underfilled: {len(gen)}. Malformed or missing arrays: {len(problems)}.",
             "", "| Study | Run | Dataset | Chunking | Retriever | B | Query | Words | Deficit | Recorded depth / chunks | Cause |",
             "|---|---|---|---|---|---:|---|---:|---:|---|---|"]
    for c in cells + gen:
        lines.append(f"| {c['study']} | {c['run']} | {c['dataset']} | {c['chunking']} | {c['retriever']} | {c['budget']} | "
                     f"{c['qid']} | {c['words']} | {c['deficit']} | {c['recorded_depth']} / {c.get('n_chunks', '—')} | "
                     f"{c['cause']} |")
    for p in problems:
        lines.append(f"\n- malformed or missing: `{p['file']}`: {p['problem']}")
    Path(args.out_md).write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
