"""Pre-registered analysis of a retrieval-multiverse run (preregistration §3.3-§5).

Usage:
  python -I -m ragmv.analyze --run experiments/E1_retrieval_multiverse/runs/<id> --label EXPLORATORY \
      --out experiments/E1_retrieval_multiverse/analysis/<id> [--reps 2000] [--joint-reps 1000]
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import stats as S
from .evaluate import METRICS
from .run import BUDGETS, KS

DATASETS = ("squad2", "covidqa", "cuad", "qasper")
DEFAULT_RETRIEVER = "lucene-k1.5-b0.75-stem"


@dataclass(frozen=True)
class Claim:
    cid: str
    role: str
    a: str
    b: str
    wmax: int  # larger chunk size in the pair: budget-matched universes need B >= wmax


def preregistered_claims() -> list[Claim]:
    claims = [Claim("P1", "primary", "fixed-128", "fixed-512", 512)]
    claims += [Claim(f"S1-{w}", "secondary", f"fixed-{w}", f"fixed-{2 * w}", 2 * w) for w in (64, 128, 256)]
    claims += [Claim(f"S2-{w}", "secondary", f"fixed-{w}-o25", f"fixed-{w}", w) for w in (64, 128, 256, 512)]
    claims += [Claim(f"S3-{w}", "secondary", f"paragraph-{w}", f"fixed-{w}", w) for w in (64, 128, 256, 512)]
    claims += [Claim(f"S4-{w}", "exploratory", f"sentence-{w}", f"fixed-{w}", w) for w in (64, 128, 256, 512)]
    return claims


class Run:
    """Lazily loads per-chunking arrays [R, n_q, ops, M] for each dataset of a run directory."""

    def __init__(self, path: Path, datasets=DATASETS):
        self.path = path
        self.meta, self.cache = {}, {}
        for d in datasets:
            mpath = path / d / "manifest.json"
            if mpath.exists():
                m = json.loads(mpath.read_text())
                if m["status"] != "ok":
                    raise RuntimeError(f"{d}: run status {m['status']}: {m['error']}")
                q = json.loads((path / d / "queries.json").read_text())
                self.meta[d] = {"manifest": m, "doc_idx": np.asarray(q["doc_idx"])}
        if not self.meta:
            raise FileNotFoundError(f"no dataset manifests under {path}")
        first = next(iter(self.meta.values()))["manifest"]["config"]
        self.retrievers = first["retrievers"]
        self.ops = first["ops"]

    @property
    def datasets(self):
        return list(self.meta)

    def scores(self, dataset: str, chunking: str) -> np.ndarray:
        key = (dataset, chunking)
        if key not in self.cache:
            self.cache[key] = np.load(self.path / dataset / f"{chunking}.npz")["scores"].astype(np.float32)
        return self.cache[key]


def op_indices(protocol: str, wmax: int, admissible: bool = True) -> list[int]:
    if protocol == "count":
        return list(range(len(KS)))
    return [len(KS) + i for i, b in enumerate(BUDGETS) if b >= wmax or not admissible]


def claim_diffs(run: Run, claim: Claim, protocol: str, admissible=True, retrievers=None, datasets=None):
    """Per dataset: per-query differences [n_q, U] and universe labels (retriever, op, metric)."""
    out = {}
    r_idx = [i for i, r in enumerate(run.retrievers) if retrievers is None or r in retrievers]
    ops = op_indices(protocol, claim.wmax, admissible)
    for d in datasets or run.datasets:
        delta = run.scores(d, claim.a) - run.scores(d, claim.b)  # [R, n, ops, M]
        delta = delta[r_idx][:, :, ops, :]  # [R', n, O, M]
        n = delta.shape[1]
        diff = np.moveaxis(delta, 1, 0).reshape(n, -1)
        labels = [(run.retrievers[r], run.ops[o], m) for r in r_idx for o in ops for m in METRICS]
        out[d] = (diff, labels)
    return out


def verdict_summary(diffs, reps, seed=7, clusters=None, bh=False):
    """Percentile-bootstrap verdicts per universe, pooled over datasets."""
    all_v, per_ds = [], {}
    for d, (diff, _) in diffs.items():
        mean, lo, hi, p = S.paired_bootstrap_ci(diff, reps=reps, seed=seed, clusters=None if clusters is None else clusters[d])
        v = S.verdicts(lo, hi)
        if bh:
            v = np.where(S.bh_reject(p), np.sign(mean).astype(np.int8), 0).astype(np.int8)
        per_ds[d] = {"support_A": float((v == 1).mean()), "support_B": float((v == -1).mean()),
                     "inconclusive": float((v == 0).mean()), "n_universes": int(v.size), "mean_delta": float(mean.mean())}
        all_v.append(v)
    v = np.concatenate(all_v)
    return {"support_A": float((v == 1).mean()), "support_B": float((v == -1).mean()),
            "inconclusive": float((v == 0).mean()), "n_universes": int(v.size), "by_dataset": per_ds}


def protocol_contrast(run, claim, side, reps, joint_reps, admissible=True, retrievers=None, datasets=None, clusters=None):
    """share(side | count) - share(side | budget); side = +1 (A) or -1 (B). Returns estimate, CI and parts."""
    dc = claim_diffs(run, claim, "count", True, retrievers, datasets)
    db = claim_diffs(run, claim, "budget", admissible, retrievers, datasets)
    key = "support_A" if side == 1 else "support_B"
    sc, sb = verdict_summary(dc, reps, clusters=clusters), verdict_summary(db, reps, clusters=clusters)
    est = sc[key] - sb[key]
    combined = {d: np.hstack([dc[d][0], db[d][0]]) for d in dc}
    split = {d: dc[d][0].shape[1] for d in dc}

    def stat(v):
        vc = np.concatenate([v[d][: split[d]] for d in v])
        vb = np.concatenate([v[d][split[d]:] for d in v])
        return float((vc == side).mean() - (vb == side).mean())

    boot = S.joint_bootstrap_shares(combined, stat, reps=joint_reps, clusters=clusters)
    lo, hi = np.quantile(boot, [0.025, 0.975])
    return {"estimate": est, "ci95": [float(lo), float(hi)], "count": sc, "budget": sb}


def hypothesis_verdict(est, lo, hi, threshold):
    if est >= threshold and lo > 0:
        return "supported"
    if hi < threshold:
        return "falsified"
    return "inconclusive"


def h2_eta(run, claim, joint_reps):
    diffs = claim_diffs(run, claim, "budget")
    labels = [(d, *lab) for d in diffs for lab in diffs[d][1]]
    factors = {name: np.array([lab[i] for lab in labels]) for i, name in enumerate(["dataset", "retriever", "budget", "metric"])}

    def etas(means_by_ds):
        y = np.concatenate([means_by_ds[d] for d in diffs])
        return S.eta_squared(y, factors)

    point = etas({d: diffs[d][0].mean(axis=0) for d in diffs})
    boot = S.joint_bootstrap({d: diffs[d][0] for d in diffs},
                             lambda st: float(max(etas({d: st[d][0] for d in st}).items(), key=lambda kv: kv[1])[0] == "dataset"),
                             reps=joint_reps, seed=13)
    frac = float(boot.mean())
    verdict = "supported" if frac >= 0.95 else ("falsified" if frac <= 0.5 else "inconclusive")
    return {"eta2": point, "dataset_largest_fraction": frac, "verdict": verdict}


def h3_power(run, claims):
    req = []
    per_claim = {}
    for c in claims:
        diffs = claim_diffs(run, c, "budget")
        r = np.concatenate([S.required_n(diffs[d][0].std(axis=0, ddof=1)) for d in diffs])
        per_claim[c.cid] = {"median_required_n": float(np.median(r)), "share_over_500": float((r > 500).mean())}
        req.append(r)
    r = np.concatenate(req)
    share = float((r > 500).mean())
    return {"share_universes_requiring_over_500": share, "median_required_n": float(np.median(r)),
            "verdict": "supported" if share > 0.5 else "falsified", "by_claim": per_claim}


def analyze(run: Run, reps=2000, joint_reps=1000) -> dict:
    claims = preregistered_claims()
    by_id = {c.cid: c for c in claims}
    clusters = {d: run.meta[d]["doc_idx"] for d in run.datasets}
    res = {"datasets": run.datasets, "n_queries": {d: int(len(run.meta[d]["doc_idx"])) for d in run.datasets}}

    res["verdict_shares"] = {
        c.cid: {"role": c.role, "A": c.a, "B": c.b,
                "count": verdict_summary(claim_diffs(run, c, "count"), reps),
                "budget": verdict_summary(claim_diffs(run, c, "budget"), reps)}
        for c in claims
    }
    h1 = protocol_contrast(run, by_id["P1"], -1, reps, joint_reps)
    h1["verdict"] = hypothesis_verdict(h1["estimate"], *h1["ci95"], 0.20)
    h1b = protocol_contrast(run, by_id["S3-256"], +1, reps, joint_reps)
    h1b["estimate"], h1b["ci95"] = -h1b["estimate"], [-h1b["ci95"][1], -h1b["ci95"][0]]  # budget - count
    h1b["verdict"] = hypothesis_verdict(h1b["estimate"], *h1b["ci95"], 0.10)
    res["H1"], res["H1b"] = h1, h1b
    res["H2"] = h2_eta(run, by_id["S3-256"], joint_reps)
    res["H3"] = h3_power(run, [c for c in claims if c.cid.startswith(("S2", "S3"))])

    sens = {}
    p1 = by_id["P1"]
    for name, kw in {
        "a_bh_fdr": None,
        "b_without_squad2": {"datasets": [d for d in run.datasets if d != "squad2"]},
        "c_default_retriever": {"retrievers": [DEFAULT_RETRIEVER]},
        "d_cluster_bootstrap": {"clusters": clusters},
        "e_all_budgets": {"admissible": False},
    }.items():
        if kw is None:
            c = verdict_summary(claim_diffs(run, p1, "count"), reps, bh=True)
            b = verdict_summary(claim_diffs(run, p1, "budget"), reps, bh=True)
            sens[name] = {"estimate": c["support_B"] - b["support_B"]}
        elif name == "b_without_squad2" and not kw["datasets"]:
            continue
        else:
            out = protocol_contrast(run, p1, -1, reps, joint_reps, **kw)
            sens[name] = {"estimate": out["estimate"], "ci95": out["ci95"]}
    res["H1_sensitivity"] = sens
    return res


def _pct(x):
    return f"{100 * x:.1f}%"


def to_markdown(res: dict, label: str) -> str:
    lines = [f"# Study 1 results — {label}", "",
             f"Datasets: {', '.join(res['datasets'])}; queries: " + ", ".join(f"{k} {v}" for k, v in res["n_queries"].items()), "",
             "## Hypotheses", "", "| ID | Estimate | 95% CI | Threshold | Verdict |", "|---|---:|---|---:|---|"]
    for h, thr in (("H1", 0.20), ("H1b", 0.10)):
        r = res[h]
        lines.append(f"| {h} | {_pct(r['estimate'])} | [{_pct(r['ci95'][0])}, {_pct(r['ci95'][1])}] | {_pct(thr)} | {r['verdict']} |")
    h2 = res["H2"]
    lines.append(f"| H2 | dataset η² largest in {_pct(h2['dataset_largest_fraction'])} of replicates | — | 95% | {h2['verdict']} |")
    h3 = res["H3"]
    lines.append(f"| H3 | {_pct(h3['share_universes_requiring_over_500'])} of universes need n > 500 (median n = {h3['median_required_n']:.0f}) | — | > 50% | {h3['verdict']} |")
    lines += ["", "H2 point estimates (η²): " + ", ".join(f"{k} {v:.3f}" for k, v in h2["eta2"].items()), "",
              "## H1 sensitivity analyses (P1: share supporting fixed-512, count − budget)", "",
              "| Analysis | Estimate | 95% CI |", "|---|---:|---|"]
    for k, v in res["H1_sensitivity"].items():
        ci = f"[{_pct(v['ci95'][0])}, {_pct(v['ci95'][1])}]" if "ci95" in v else "—"
        lines.append(f"| {k} | {_pct(v['estimate'])} | {ci} |")
    lines += ["", "## Verdict shares per claim and protocol", "",
              "| Claim | Role | A vs B | Protocol | Universes | Supports A | Supports B | Inconclusive |",
              "|---|---|---|---|---:|---:|---:|---:|"]
    for cid, v in res["verdict_shares"].items():
        for prot in ("count", "budget"):
            s = v[prot]
            lines.append(f"| {cid} | {v['role']} | {v['A']} vs {v['B']} | {prot} | {s['n_universes']} | "
                         f"{_pct(s['support_A'])} | {_pct(s['support_B'])} | {_pct(s['inconclusive'])} |")
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
    res["source_manifests"] = {d: {k: run.meta[d]["manifest"][k] for k in ("git", "config_sha256", "started_utc")} for d in run.datasets}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=2))
    (out / "results.md").write_text(to_markdown(res, args.label))
    print((out / "results.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
