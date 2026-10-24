"""Tier 2 (exploratory) analysis: does the retrieval-level protocol reversal carry over to answer quality?

Usage:
  python -I -m ragmv.analyze_generation --run experiments/E2_generation/runs/<id> \
      --out experiments/E2_generation/analysis/<id>

Plan (fixed before any Tier 2 result was seen): `experiments/E2_generation/ANALYSIS_PLAN.md`.
For claim (A, B) and operating point o, d_q(o) = F1_q(A, o) - F1_q(B, o). The reversal statistic is the
difference-in-differences DiD_q = d_q(budget1024) - d_q(count5); E1 predicts DiD > 0 for both claims.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from . import stats as S
from .generate import read_rows

DATASETS = ("squad2", "covidqa", "cuad", "qasper")
CLAIMS = {"P1": ("fixed-128", "fixed-512"), "S3-256": ("paragraph-256", "fixed-256")}
OPS = ("count5", "budget1024")
METRICS = ("f1", "em")
RETRIEVAL_METRICS = ("hit_strict", "hit_lenient", "coverage")


def load_rows(path: Path) -> list[dict]:
    """Last successful row per job_id (earlier error rows of a resumed run are superseded)."""
    rows = {}
    for row in read_rows(path):
        if row.get("status") == "ok":
            rows[row["job_id"]] = row
    return list(rows.values())


def table(rows: list[dict], field: str) -> tuple[list[str], dict[tuple[str, str], np.ndarray]]:
    """Complete-case table: qids with every (chunking, op) cell present -> {(chunking, op): values[n]}."""
    cells = {}
    for r in rows:
        val = r[field] if field in r else r["retrieval"][field]
        cells[(r["qid"], r["chunking"], r["op"])] = float(val)
    needed = [(c, o) for pair in CLAIMS.values() for c in pair for o in OPS]
    qids = sorted({q for q, _, _ in cells})
    qids = [q for q in qids if all((q, c, o) in cells for c, o in needed)]
    return qids, {(c, o): np.array([cells[(q, c, o)] for q in qids]) for c, o in needed}


def per_query_contrasts(tab: dict, claim: str) -> dict[str, np.ndarray]:
    a, b = CLAIMS[claim]
    d = {o: tab[(a, o)] - tab[(b, o)] for o in OPS}
    d["did"] = d["budget1024"] - d["count5"]
    return d


def stratified_ci(per_dataset: dict[str, np.ndarray], reps: int = 2000, seed: int = 7, alpha: float = 0.05):
    """Equal-weight mean over datasets of per-dataset means; queries resampled within each dataset."""
    rng = np.random.default_rng(seed)
    names = sorted(per_dataset)
    point = float(np.mean([per_dataset[k].mean() for k in names]))
    boot = np.zeros(reps)
    for k in names:
        x = per_dataset[k]
        w = rng.multinomial(len(x), np.full(len(x), 1.0 / len(x)), size=reps)
        boot += (w @ x) / len(x)
    boot /= len(names)
    lo, hi = np.quantile(boot, [alpha / 2, 1 - alpha / 2])
    return point, float(lo), float(hi)


def verdict(lo: float, hi: float) -> str:
    return "carries over" if lo > 0 else "opposite" if hi < 0 else "inconclusive"


def summarise(x: np.ndarray, reps: int, seed: int = 7) -> dict:
    m, lo, hi, _ = S.paired_bootstrap_ci(x[:, None], reps=reps, seed=seed)
    return {"mean": float(m[0]), "lo": float(lo[0]), "hi": float(hi[0]), "n": int(len(x))}


def diagnostics(raw_lines: list[dict], rows: list[dict]) -> dict:
    usage = Counter()
    for r in rows:
        for k in ("prompt_token_count", "candidates_token_count", "thoughts_token_count"):
            usage[k] += int((r.get("usage") or {}).get(k) or 0)
    return {
        "rows_total": len(raw_lines), "jobs_ok": len(rows),
        "status_counts": dict(Counter(r.get("status") for r in raw_lines)),
        "finish_reasons": dict(Counter(str(r.get("finish_reason")) for r in rows)),
        "served_model_versions": dict(Counter(str(r.get("model_version")) for r in rows)),
        "requested_models": dict(Counter(str(r.get("model")) for r in rows)),
        "unanswerable_rate": float(np.mean([r["response"].strip().lower().startswith("unanswerable") for r in rows]))
        if rows else None,
        "usage_totals": dict(usage),
    }


def analyse(run: Path, reps: int = 2000) -> dict:
    out = {"label": "EXPLORATORY (Tier 2; pre-specified plan, not part of the frozen confirmatory hypotheses)",
           "datasets": {}, "pooled": {}}
    did = {c: {m: {} for m in METRICS + ("coverage",)} for c in CLAIMS}
    for ds in DATASETS:
        path = run / ds / "generations.jsonl"
        if not path.exists():
            continue
        raw = read_rows(path)
        rows = load_rows(path)
        dsout = {"diagnostics": diagnostics(raw, rows), "claims": {}, "means": {}}
        tabs = {}
        for field in METRICS + RETRIEVAL_METRICS:
            qids, tabs[field] = table(rows, field)
        dsout["n_complete_queries"] = len(qids)
        if not qids:
            out["datasets"][ds] = dsout
            continue
        dsout["means"] = {f"{c}|{o}": {f: float(tabs[f][(c, o)].mean()) for f in METRICS + RETRIEVAL_METRICS}
                          for c, o in tabs["f1"]}
        for claim in CLAIMS:
            cl = {}
            for field in METRICS + ("coverage",):
                con = per_query_contrasts(tabs[field], claim)
                cl[field] = {k: summarise(v, reps) for k, v in con.items()}
                for o in OPS:
                    cl[field][o]["verdict"] = {1: "supports A", -1: "supports B", 0: "inconclusive"}[
                        int(S.verdicts(np.array([cl[field][o]["lo"]]), np.array([cl[field][o]["hi"]]))[0])]
                cl[field]["did"]["sd"] = float(con["did"].std(ddof=1)) if len(con["did"]) > 1 else None
                did[claim][field][ds] = con["did"]
            dsout["claims"][claim] = cl
        f1 = np.array([r["f1"] for r in rows])
        cov = np.array([r["retrieval"]["coverage"] for r in rows])
        hit = np.array([r["retrieval"]["hit_lenient"] for r in rows])
        dsout["retrieval_answer_link"] = {
            "pearson_coverage_f1": float(np.corrcoef(cov, f1)[0, 1]) if cov.std() > 0 and f1.std() > 0 else None,
            "mean_f1_hit_lenient_1": float(f1[hit == 1].mean()) if (hit == 1).any() else None,
            "mean_f1_hit_lenient_0": float(f1[hit == 0].mean()) if (hit == 0).any() else None,
        }
        out["datasets"][ds] = dsout
    for claim in CLAIMS:
        out["pooled"][claim] = {}
        for field, per_ds in did[claim].items():
            if not per_ds:
                continue
            point, lo, hi = stratified_ci(per_ds, reps=reps)
            n = sum(len(v) for v in per_ds.values())
            sd = float(np.std(np.concatenate(list(per_ds.values())), ddof=1)) if n > 1 else None
            out["pooled"][claim][field] = {
                "did": point, "lo": lo, "hi": hi, "n": n, "datasets": sorted(per_ds),
                "verdict": verdict(lo, hi),
                # minimum detectable DiD at alpha 0.05, power 0.8 (normal approximation, observed SD)
                "mde": float((S.Z_975 + S.Z_80) * sd / np.sqrt(n)) if sd else None,
            }
    return out


def to_markdown(res: dict) -> str:
    lines = [f"# E2 Tier 2 generation — {res['label']}", "",
             "DiD = Δ(budget 1,024 words) − Δ(top-5), Δ = metric(A) − metric(B). E1 predicts DiD > 0 for both claims.",
             "", "## Pooled (equal weight per dataset, stratified bootstrap, 2,000 resamples)", "",
             "| Claim | Measure | DiD | 95% CI | n | MDE | Verdict |", "|---|---|---:|---|---:|---:|---|"]
    for claim, fields in res["pooled"].items():
        for field, r in fields.items():
            mde = f"{r['mde']:.3f}" if r["mde"] is not None else "—"
            lines.append(f"| {claim} | {field} | {r['did']:+.3f} | [{r['lo']:+.3f}, {r['hi']:+.3f}] | {r['n']} | {mde} "
                         f"| {r['verdict']} |")
    lines += ["", "## Per dataset (answer F1)", "",
              "| Dataset | Claim | Δ top-5 [CI] | Δ budget-1,024 [CI] | DiD [CI] | n |", "|---|---|---|---|---|---:|"]
    for ds, d in res["datasets"].items():
        for claim, cl in d.get("claims", {}).items():
            f = cl["f1"]
            cell = lambda r: f"{r['mean']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}]"  # noqa: E731
            lines.append(f"| {ds} | {claim} | {cell(f['count5'])} | {cell(f['budget1024'])} | {cell(f['did'])} "
                         f"| {f['did']['n']} |")
    lines += ["", "## Diagnostics", ""]
    for ds, d in res["datasets"].items():
        g = d["diagnostics"]
        lines.append(f"- **{ds}**: {g['jobs_ok']} ok jobs, complete queries {d['n_complete_queries']}; status "
                     f"{g['status_counts']}; finish {g['finish_reasons']}; served {g['served_model_versions']}; "
                     f"unanswerable rate {g['unanswerable_rate']:.3f}" if g["unanswerable_rate"] is not None
                     else f"- **{ds}**: no successful rows")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--reps", type=int, default=2000)
    args = ap.parse_args(argv)
    res = analyse(Path(args.run), args.reps)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=2))
    (out / "results.md").write_text(to_markdown(res))
    print(to_markdown(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
