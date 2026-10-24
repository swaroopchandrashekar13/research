
"""Pre-registered analysis of a Study 1b run (research/preregistration_study1b.md §4-§5).

Usage:
  python -I -m ragmv.analyze1b --run experiments/E3_semantic_dense/runs/<id> --label EXPLORATORY --out <dir>

H4/H4b are stated for "the shorter arm": for each (dataset, claim instance) the arm with the smaller mean chunk length
(from the run manifest's chunk statistics, i.e. chunking only, before any metric) is oriented as the positive side.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import stats as S
from .analyze import Claim, Run, claim_diffs, hypothesis_verdict, protocol_contrast, verdict_summary

WIDTHS = (128, 256, 512)


def study1b_claims() -> dict[str, list[Claim]]:
    """Every arm involving a semantic chunker or fixed-512 is capped at 512 words: admissible budgets B >= 512."""
    return {
        "S5": [Claim(f"S5-{w}", "primary", "semantic-bp", f"fixed-{w}", 512) for w in WIDTHS],
        "S6": [Claim(f"S6-{w}", "secondary", "semantic-cl", f"fixed-{w}", 512) for w in WIDTHS],
        "P1": [Claim("P1", "secondary", "fixed-128", "fixed-512", 512)],
    }


def mean_lengths(run: Run) -> dict[str, dict[str, float]]:
    return {d: {s["chunking"]: s["chunk_words_mean"] for s in run.meta[d]["manifest"]["chunk_stats"]} for d in run.datasets}


def oriented(run, claims, protocol, lengths, admissible=True, retrievers=None, datasets=None):
    """Per dataset: per-query differences oriented so that + means the shorter arm is better, all instances stacked."""
    out = {}
    for c in claims:
        for d, (diff, labels) in claim_diffs(run, c, protocol, admissible, retrievers, datasets).items():
            sign = 1.0 if lengths[d][c.a] <= lengths[d][c.b] else -1.0
            prev = out.get(d, (np.zeros((diff.shape[0], 0)), []))
            out[d] = (np.hstack([prev[0], sign * diff]), prev[1] + [(c.cid, *lab) for lab in labels])
    return out


def shorter_contrast(run, claims, lengths, reps, joint_reps, admissible=True, retrievers=None, datasets=None,
                     clusters=None, bh=False):
    """share(shorter arm supported | budget) - share(... | count), with a joint-bootstrap CI."""
    dc = oriented(run, claims, "count", lengths, True, retrievers, datasets)
    db = oriented(run, claims, "budget", lengths, admissible, retrievers, datasets)
    sc = verdict_summary(dc, reps, clusters=clusters, bh=bh)
    sb = verdict_summary(db, reps, clusters=clusters, bh=bh)
    est = sb["support_A"] - sc["support_A"]
    if bh:
        return {"estimate": est}
    combined = {d: np.hstack([dc[d][0], db[d][0]]) for d in dc}
    split = {d: dc[d][0].shape[1] for d in dc}

    def stat(v):
        vc = np.concatenate([v[d][: split[d]] for d in v])
        vb = np.concatenate([v[d][split[d]:] for d in v])
        return float((vb == 1).mean() - (vc == 1).mean())

    boot = S.joint_bootstrap_shares(combined, stat, reps=joint_reps, clusters=clusters)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return {"estimate": est, "ci95": [float(lo), float(hi)], "count_share": sc["support_A"], "budget_share": sb["support_A"]}


def analyze(run: Run, reps=2000, joint_reps=1000) -> dict:
    claims = study1b_claims()
    lengths = mean_lengths(run)
    clusters = {d: run.meta[d]["doc_idx"] for d in run.datasets}
    res = {"datasets": run.datasets, "n_queries": {d: int(len(run.meta[d]["doc_idx"])) for d in run.datasets},
           "mean_chunk_words": lengths,
           "shorter_arm": {c.cid: {d: (c.a if lengths[d][c.a] <= lengths[d][c.b] else c.b) for d in run.datasets}
                           for c in claims["S5"] + claims["S6"]}}
    h4 = shorter_contrast(run, claims["S5"], lengths, reps, joint_reps)
    h4["verdict"] = hypothesis_verdict(h4["estimate"], *h4["ci95"], 0.20)
    h4b = shorter_contrast(run, claims["S6"], lengths, reps, joint_reps)
    h4b["verdict"] = hypothesis_verdict(h4b["estimate"], *h4b["ci95"], 0.10)
    h5 = protocol_contrast(run, claims["P1"][0], -1, reps, joint_reps, retrievers=["dense"])
    h5["verdict"] = hypothesis_verdict(h5["estimate"], *h5["ci95"], 0.20)
    # H5b (post-pilot amendment, v1.0 §9): the same protocol contrast as H4, for P1 with the dense retriever
    h5b = shorter_contrast(run, claims["P1"], lengths, reps, joint_reps, retrievers=["dense"])
    h5b["verdict"] = hypothesis_verdict(h5b["estimate"], *h5b["ci95"], 0.20)
    res.update(H4=h4, H4b=h4b, H5=h5, H5b=h5b)

    sens = {"a_bh_fdr": shorter_contrast(run, claims["S5"], lengths, reps, joint_reps, bh=True)}
    if [d for d in run.datasets if d != "squad2"] and "squad2" in run.datasets:
        sens["b_without_squad2"] = shorter_contrast(run, claims["S5"], lengths, reps, joint_reps,
                                                    datasets=[d for d in run.datasets if d != "squad2"])
    sens["d_cluster_bootstrap"] = shorter_contrast(run, claims["S5"], lengths, reps, joint_reps, clusters=clusters)
    sens["e_all_budgets"] = shorter_contrast(run, claims["S5"], lengths, reps, joint_reps, admissible=False)
    for r in run.retrievers:  # (f) per retriever
        sens[f"f_{r}_only"] = shorter_contrast(run, claims["S5"], lengths, reps, joint_reps, retrievers=[r])
    res["H4_sensitivity"] = sens

    # (g) descriptive: share of universes supporting the SEMANTIC arm (the quantity Qu et al. report)
    res["semantic_wins"] = {
        c.cid: {prot: verdict_summary(claim_diffs(run, c, prot), reps) for prot in ("count", "budget")}
        for c in claims["S5"] + claims["S6"]
    }
    return res


def _pct(x):
    return f"{100 * x:.1f}%"


def to_markdown(res: dict, label: str) -> str:
    lines = [f"# Study 1b results — {label}", "",
             "Queries: " + ", ".join(f"{k} {v}" for k, v in res["n_queries"].items()), "",
             "## Hypotheses", "", "| ID | Estimate | 95% CI | Threshold | Verdict |", "|---|---:|---|---:|---|"]
    for h, thr in (("H4", 0.20), ("H4b", 0.10), ("H5", 0.20), ("H5b", 0.20)):
        r = res[h]
        lines.append(f"| {h} | {_pct(r['estimate'])} | [{_pct(r['ci95'][0])}, {_pct(r['ci95'][1])}] | {_pct(thr)} | {r['verdict']} |")
    lines += ["", "## H4 sensitivity (share supporting the shorter arm, budget − count)", "",
              "| Analysis | Estimate | 95% CI |", "|---|---:|---|"]
    for k, v in res["H4_sensitivity"].items():
        ci = f"[{_pct(v['ci95'][0])}, {_pct(v['ci95'][1])}]" if "ci95" in v else "—"
        lines.append(f"| {k} | {_pct(v['estimate'])} | {ci} |")
    lines += ["", "## Mean chunk length (words) and the shorter arm", "",
              "| Dataset | " + " | ".join(next(iter(res["mean_chunk_words"].values()))) + " |",
              "|---|" + "---:|" * len(next(iter(res["mean_chunk_words"].values())))]
    for d, m in res["mean_chunk_words"].items():
        lines.append(f"| {d} | " + " | ".join(f"{v:.0f}" for v in m.values()) + " |")
    lines += ["", "## Semantic arm supported (descriptive, sensitivity g)", "",
              "| Claim | Protocol | Universes | Supports semantic | Supports fixed | Inconclusive |", "|---|---|---:|---:|---:|---:|"]
    for cid, v in res["semantic_wins"].items():
        for prot in ("count", "budget"):
            s = v[prot]
            lines.append(f"| {cid} | {prot} | {s['n_universes']} | {_pct(s['support_A'])} | {_pct(s['support_B'])} | {_pct(s['inconclusive'])} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True, choices=["EXPLORATORY", "CONFIRMATORY", "SMOKE"])
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--joint-reps", type=int, default=1000)
    args = ap.parse_args(argv)
    run = Run(Path(args.run))
    res = analyze(run, args.reps, args.joint_reps)
    res["label"] = args.label
    res["source_manifests"] = {d: {k: run.meta[d]["manifest"][k] for k in ("git", "config_sha256", "started_utc", "encoder")}
                               for d in run.datasets}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=2))
    (out / "results.md").write_text(to_markdown(res, args.label))
    print((out / "results.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
