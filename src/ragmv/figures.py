"""Paper figures generated from logged results only (never from hand-typed numbers).

Usage:
  python -I -m ragmv.figures --run <Study 1 run dir> --results <its results.json> --out <new dir> --label CONFIRMATORY
  python -I -m ragmv.figures --study 1b --results <Study 1b results.json> --out <new dir> --label CONFIRMATORY

The verdict dumbbells plot the shares stored in the validated `results.json` (the analysis' own 2,000-resample
verdicts), not a fresh recomputation. Specification curves recompute per-universe intervals from the run arrays with
the resample count and seed recorded in `results.json` (`analysis_settings`, default 2,000 / seed 7). Every figure
writes `<stem>.coords.json` with the exact plotted coordinates, so each point can be checked against its source.
Encoding (validated palette): count-matched = blue filled circle, budget-matched = orange open square, so the two
protocols stay distinguishable in grayscale print.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from . import stats as S  # noqa: E402
from .analyze import SEEDS, Run, claim_diffs, planned_claims  # noqa: E402
from .integrity import atomic_write_text  # noqa: E402

DUMBBELL_CLAIMS = ["P1", "S1-64", "S1-128", "S1-256", "S2-128", "S2-256", "S3-128", "S3-256", "S3-512", "S4-256"]


def _write_coords(out: Path, stem: str, payload: dict) -> None:
    atomic_write_text(out / f"{stem}.coords.json", json.dumps(payload, indent=1))

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#ffffff"
PROTOCOL_STYLE = {
    "count": {"color": "#2a78d6", "marker": "o", "mfc": "#2a78d6", "label": "count-matched (top-k)"},
    "budget": {"color": "#eb6834", "marker": "s", "mfc": "none", "label": "budget-matched (equal words)"},
}
DATASET_TITLES = {"squad2": "SQuAD 2.0 (Wikipedia)", "covidqa": "COVID-QA (biomedical)",
                  "cuad": "CUAD (contracts)", "qasper": "Qasper (NLP papers)"}


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(colors=INK2, labelsize=8, width=0.8)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def specification_curve(run: Run, cid: str, metric: str, out: Path, label: str, reps: int = 2000,
                        seed: int = SEEDS["verdict_bootstrap"], publication: bool = False):
    """One panel per dataset. `publication`: 2x2 panels, legend below, no in-figure title (for the manuscript)."""
    claim = next(c for c in planned_claims() if c.cid == cid)
    coords = {"claim": cid, "metric": metric, "reps": reps, "seed": seed, "panels": {}}
    n = len(run.datasets)
    cols = min(2, n) if publication else n
    rows = -(-n // cols)
    size = (3.4 * cols, 2.5 * rows + 0.4) if publication else (3.0 * n, 2.8)
    fig, axes = plt.subplots(rows, cols, figsize=size, sharey=True, squeeze=False)
    axes = axes.ravel()
    for ax in axes[n:]:
        ax.set_visible(False)
    for i, (ax, d) in enumerate(zip(axes, run.datasets)):
        _style(ax)
        pts = []
        for prot in ("count", "budget"):
            diff, labels = claim_diffs(run, claim, prot, datasets=[d])[d]
            keep = [i for i, lab in enumerate(labels) if lab[2] == metric]
            mean, lo, hi, _ = S.paired_bootstrap_ci(diff[:, keep], reps=reps, seed=seed)
            pts += [(float(m), float(l), float(h), prot, labels[k]) for m, l, h, k in zip(mean, lo, hi, keep)]
        pts.sort(key=lambda t: t[0])
        coords["panels"][d] = [{"x": i, "mean": p[0], "lo": p[1], "hi": p[2], "protocol": p[3],
                                "universe": list(p[4])} for i, p in enumerate(pts)]
        x = np.arange(len(pts))
        ax.axhline(0, color=MUTED, linewidth=0.8, zorder=1)
        for prot, st in PROTOCOL_STYLE.items():
            idx = [i for i, p in enumerate(pts) if p[3] == prot]
            m = np.array([pts[i][0] for i in idx])
            err = np.array([[pts[i][0] - pts[i][1] for i in idx], [pts[i][2] - pts[i][0] for i in idx]])
            ax.errorbar(x[idx], m, yerr=err, fmt=st["marker"], ms=3.2, mfc=st["mfc"], mec=st["color"], mew=0.9,
                        ecolor=st["color"], elinewidth=0.6, capsize=0, label=st["label"], zorder=2)
        ax.set_title(DATASET_TITLES.get(d, d), fontsize=9, color=INK)
        ax.set_xticks([])
        if not publication or i >= n - cols:
            ax.set_xlabel("universes, sorted by effect", fontsize=8, color=INK2)
        if i % cols == 0:
            ax.set_ylabel(f"Δ {metric}  ({claim.a} − {claim.b})", fontsize=8, color=INK)
    if publication:
        handles, names = axes[0].get_legend_handles_labels()
        fig.legend(handles, names, loc="lower center", ncol=2, fontsize=8, frameon=False, labelcolor=INK2)
        fig.tight_layout(rect=(0, 0.06, 1, 1))
    else:
        axes[n - 1].legend(loc="lower right", fontsize=7, frameon=False, labelcolor=INK2)
        fig.suptitle(f"{cid}: {claim.a} vs {claim.b} — 95% paired-bootstrap CIs  [{label}]", fontsize=9.5, color=INK,
                     x=0.01, ha="left")
        fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out / f"speccurve_{cid}_{metric}.{ext}", dpi=200, facecolor=SURFACE)
    plt.close(fig)
    _write_coords(out, f"speccurve_{cid}_{metric}", coords)


def verdict_dumbbell(results: dict, cids: list[str], out: Path, label: str, publication: bool = False):
    """Net verdict = share(A significantly better) - share(B significantly better), per protocol, read from the
    validated Study 1 results.json (no independent recomputation with a different resample count)."""
    shares = results["verdict_shares"]
    missing = [c for c in cids if c not in shares]
    if missing:
        raise KeyError(f"claims {missing} not in results.json")
    rows = [(f"{c}: {shares[c]['A']} vs {shares[c]['B']}",
             {p: shares[c][p]["support_A"] - shares[c][p]["support_B"] for p in PROTOCOL_STYLE}) for c in cids]
    _dumbbell(rows, out, "verdict_dumbbell", None if publication else f"Chunking verdicts by selection protocol  [{label}]")


def study1b_dumbbell(results: dict, out: Path, label: str, publication: bool = False):
    """Same encoding as verdict_dumbbell, from the shares stored in a Study 1b results.json (analyze1b)."""
    rows = []
    for cid, v in results["semantic_wins"].items():
        a = "semantic-bp" if cid.startswith("S5") else "semantic-cl"
        rows.append((f"{cid}: {a} vs fixed-{cid.split('-')[1]}",
                     {p: v[p]["support_A"] - v[p]["support_B"] for p in PROTOCOL_STYLE}))
    rows.append(("P1-dense: fixed-128 vs fixed-512",
                 {p: results["H5"][p]["support_A"] - results["H5"][p]["support_B"] for p in PROTOCOL_STYLE}))
    _dumbbell(rows, out, "study1b_dumbbell",
              None if publication else f"Semantic chunking and dense retrieval by selection protocol  [{label}]")


def _dumbbell(rows: list[tuple[str, dict]], out: Path, stem: str, title: str | None):
    fig, ax = plt.subplots(figsize=(7.0, 0.36 * len(rows) + 1.3))
    _style(ax)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.grid(axis="y", visible=False)
    ax.axvline(0, color=MUTED, linewidth=0.8, zorder=1)
    for y, (_, net) in enumerate(rows):
        ax.plot([net["count"], net["budget"]], [y, y], color=GRID, linewidth=2.2, zorder=1)
        for p, st in PROTOCOL_STYLE.items():
            ax.plot(net[p], y, st["marker"], ms=6.5, mfc=st["mfc"] if st["mfc"] != "none" else SURFACE,
                    mec=st["color"], mew=1.4, zorder=2, label=st["label"] if y == 0 else None)
    ax.set_yticks(range(len(rows)), [name for name, _ in rows], fontsize=8, color=INK)
    ax.set_xlim(-1.05, 1.05)
    ax.set_xticks([-1, -0.5, 0, 0.5, 1])
    ax.set_xlabel("net share of universes:  A significantly better − B significantly better", fontsize=8, color=INK2)
    ax.invert_yaxis()
    ax.text(-1.0, len(rows) - 0.35, "← B wins", fontsize=7.5, color=INK2, va="center")
    ax.text(1.0, len(rows) - 0.35, "A wins →", fontsize=7.5, color=INK2, ha="right", va="center")
    ax.set_ylim(len(rows) - 0.1, -0.6)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=7.5, frameon=False, labelcolor=INK2)
    if title:
        fig.suptitle(title, fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out / f"{stem}.{ext}", dpi=200, facecolor=SURFACE)
    plt.close(fig)
    _write_coords(out, stem, {"rows": [{"label": name, "count": net["count"], "budget": net["budget"]}
                                       for name, net in rows]})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", choices=("1", "1b"), default="1")
    ap.add_argument("--run", help="Study 1 run directory (specification curves)")
    ap.add_argument("--results", required=True, help="validated results.json of the same run")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--publication", action="store_true",
                    help="manuscript layout: no in-figure titles, specification curves as 2x2 panels")
    args = ap.parse_args(argv)
    results = json.loads(Path(args.results).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.study == "1b":
        study1b_dumbbell(results, out, args.label, args.publication)
    else:
        if not args.run:
            ap.error("--run is required for Study 1 figures")
        settings = results.get("analysis_settings") or {}
        reps = settings.get("verdict_bootstrap_resamples", 2000)
        seed = (settings.get("seeds") or {}).get("verdict_bootstrap", SEEDS["verdict_bootstrap"])
        run = Run(Path(args.run))
        for cid in ("P1", "S3-256"):
            specification_curve(run, cid, "coverage", out, args.label, reps=reps, seed=seed,
                                publication=args.publication)
        verdict_dumbbell(results, DUMBBELL_CLAIMS, out, args.label, args.publication)
    print(f"figures written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
