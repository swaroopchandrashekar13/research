"""Pre-registered analysis of a Study 1b run (research/preregistration_study1b.md §4-§5).

Usage:
  python -I -m ragmv.analyze1b --run experiments/E3_semantic_dense/runs/<id> --label EXPLORATORY --out <dir>

H4/H4b are stated for "the shorter arm": for each (dataset, claim instance) the arm with the smaller mean chunk length
(from the run manifest's chunk statistics, i.e. chunking only, before any metric) is oriented as the positive side.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from . import stats as S
from .analyze import (LABELS, SEEDS, Claim, Run, RunValidationError, _settings_line, analysis_settings, claim_diffs,
                      hypothesis_verdict, label_banner, positive_int, prepare_out, protocol_contrast, verdict_summary)
from .integrity import atomic_write_text, source_digest

WIDTHS = (128, 256, 512)


def study1b_claims() -> dict[str, list[Claim]]:
    """Every arm involving a semantic chunker or fixed-512 is capped at 512 words: admissible budgets B >= 512."""
    return {
        "S5": [Claim(f"S5-{w}", "primary", "semantic-bp", f"fixed-{w}", 512) for w in WIDTHS],
        "S6": [Claim(f"S6-{w}", "secondary", "semantic-cl", f"fixed-{w}", 512) for w in WIDTHS],
        "P1": [Claim("P1", "secondary", "fixed-128", "fixed-512", 512)],
    }


CHUNKINGS = ("fixed-128", "fixed-256", "fixed-512", "semantic-bp", "semantic-cl")
RETRIEVERS = ("bm25", "dense")


def mean_lengths(run: Run) -> dict[str, dict[str, float]]:
    """Mean chunk length (words, full retrieval corpus) per dataset and chunking, from the run manifests' chunk
    statistics, which the runner computes before any retrieval metric (pre-registration §3.5 item 5)."""
    out = {}
    for d in run.datasets:
        stats = run.meta[d]["manifest"].get("chunk_stats")
        if not stats:
            raise RunValidationError(f"{d}: manifest has no chunk_stats; the shorter arm cannot be determined")
        out[d] = {s["chunking"]: s["chunk_words_mean"] for s in stats}
    return out


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

    boot = S.joint_bootstrap_shares(combined, stat, reps=joint_reps, seed=SEEDS["joint_bootstrap"], clusters=clusters)
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
    # H5b (post-pilot amendment, logged in the pre-registration's deviation log, §8): H4's contrast for P1, dense only
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
    lines = [f"# Study 1b results — {label}", ""] + label_banner(label) + [
             "Queries: " + ", ".join(f"{k} {v}" for k, v in res["n_queries"].items()), ""]
    if _settings_line(res):
        lines += [_settings_line(res), ""]
    lines += ["## Hypotheses", "", "| ID | Estimate | 95% CI | Threshold | Verdict |", "|---|---:|---|---:|---|"]
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
    if res.get("validation", {}).get("legacy_limitations"):
        lines += ["", "## Legacy limitations of the input manifests (reported, not filled in)", ""]
        lines += [f"- {x}" for x in res["validation"]["legacy_limitations"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True, choices=LABELS)
    ap.add_argument("--reps", type=positive_int, default=2000)
    ap.add_argument("--joint-reps", type=positive_int, default=1000)
    ap.add_argument("--overwrite", action="store_true", help="allow writing into a non-empty output directory")
    args = ap.parse_args(argv)
    try:
        run = Run(Path(args.run), study="1b")
        validation = run.validate(args.label, list(CHUNKINGS),
                                  {"chunkings": list(CHUNKINGS), "retrievers": list(RETRIEVERS)})
        mean_lengths(run)
    except (RunValidationError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out)
    prepare_out(out, args.overwrite)
    res = analyze(run, args.reps, args.joint_reps)
    res["label"] = args.label
    res["analysis_settings"] = analysis_settings(args.reps, args.joint_reps)
    res["validation"] = {**validation, "legacy_limitations": run.legacy}
    res["code_sha256"] = source_digest()["sha256"]
    res["source_manifests"] = {d: {k: run.meta[d]["manifest"].get(k) for k in ("config_sha256", "started_utc", "encoder")}
                               for d in run.datasets}
    atomic_write_text(out / "results.json", json.dumps(res, indent=2))
    atomic_write_text(out / "results.md", to_markdown(res, args.label))
    print((out / "results.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
