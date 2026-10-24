"""Independent statistical verification of the stored Study 1, Study 1b and Tier 2 results.

This file deliberately does not import `ragmv.stats` or `ragmv.analyze`: it re-implements, from the pre-registration
text, the verdict rule, the paired percentile bootstrap (same documented RNG design so results can match exactly),
share arithmetic, the joint query bootstrap for share CIs, eta^2 (cross-checked with statsmodels OLS type II), the H3
sample-size rule and the hypothesis rules, reading the NPZ arrays directly. It then runs labelled POST-HOC
sensitivity checks that are *not* pre-registered: Monte-Carlo seed robustness, the Benjamini-Hochberg family,
universe weighting, a document-cluster design effect for H3, and verdict margins relative to float16 rounding.

Usage: python -I tools/independent_stats.py --out-json FILE --out-md FILE [--posthoc-word64 DIR]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "experiments/E1_retrieval_multiverse"
E3 = ROOT / "experiments/E3_semantic_dense"
E2 = ROOT / "experiments/E2_generation"
DATASETS = ("squad2", "covidqa", "cuad", "qasper")
Z975, Z80 = 1.959963984540054, 0.8416212335729143


# ------------------------------------------------------------------------------------------------ primitives
def load_run(path: Path):
    out = {}
    for d in DATASETS:
        m = json.loads((path / d / "manifest.json").read_text())
        q = json.loads((path / d / "queries.json").read_text())
        out[d] = {"cfg": m["config"], "manifest": m, "doc": np.asarray(q["doc_idx"]), "npz": path / d}
    return out


def scores(run, d, chunking):
    with np.load(run[d]["npz"] / f"{chunking}.npz", allow_pickle=False) as z:
        return z["scores"].astype(np.float32)


def op_cols(cfg, protocol, wmax, admissible=True):
    cols = []
    for i, lab in enumerate(cfg["ops"]):
        kind, val = lab[0], int(lab[1:])
        if protocol == "count" and kind == "k":
            cols.append(i)
        if protocol == "budget" and kind == "B" and (val >= wmax or not admissible):
            cols.append(i)
    return cols


def diffs(run, d, a, b, protocol, wmax, retrievers=None, admissible=True):
    cfg = run[d]["cfg"]
    r = [i for i, name in enumerate(cfg["retrievers"]) if retrievers is None or name in retrievers]
    delta = (scores(run, d, a) - scores(run, d, b))[r][:, :, op_cols(cfg, protocol, wmax, admissible), :]
    n = delta.shape[1]
    return np.transpose(delta, (1, 0, 2, 3)).reshape(n, -1)  # [queries, universes]


def weights(n, reps, seed, clusters=None):
    rng = np.random.default_rng(seed)
    if clusters is None:
        return rng.multinomial(n, np.full(n, 1.0 / n), size=reps).astype(np.float32)
    ids, inv = np.unique(clusters, return_inverse=True)
    return rng.multinomial(len(ids), np.full(len(ids), 1.0 / len(ids)), size=reps).astype(np.float32)[:, inv]


def percentile_verdicts(x, reps=2000, seed=7, clusters=None):
    x = np.asarray(x, dtype=np.float32)
    w = weights(x.shape[0], reps, seed, clusters)
    boot = (w @ x) / w.sum(axis=1, keepdims=True)
    lo, hi = np.quantile(boot, [0.025, 0.975], axis=0)
    v = np.zeros(x.shape[1], dtype=np.int8)
    v[lo > 0], v[hi < 0] = 1, -1
    p = np.minimum(1.0, 2 * np.minimum((boot <= 0).mean(axis=0), (boot >= 0).mean(axis=0)))
    return v, lo, hi, x.mean(axis=0), p


def shares(vs):
    v = np.concatenate(vs)
    return {"A": float((v == 1).mean()), "B": float((v == -1).mean()), "n": int(v.size)}


def bh(p, q=0.05):
    order = np.argsort(p)
    ok = p[order] <= q * np.arange(1, len(p) + 1) / len(p)
    k = ok.nonzero()[0].max() + 1 if ok.any() else 0
    out = np.zeros(len(p), bool)
    out[order[:k]] = True
    return out


def joint_share_ci(blocks, side_stat, reps=1000, seed=11):
    """Joint bootstrap: per replicate, one multinomial query resample per dataset (in dataset order), shared by all
    universes of that dataset; normal-approximation verdicts inside each replicate."""
    rng = np.random.default_rng(seed)
    out = np.empty(reps)
    for r in range(reps):
        verdicts = {}
        for d, x in blocks.items():
            n = x.shape[0]
            w = rng.multinomial(n, np.full(n, 1.0 / n)).astype(np.float64)
            ne = w.sum()
            m = w @ x / ne
            sd = np.sqrt(np.maximum(w @ (x * x) / ne - m * m, 0.0) * ne / max(ne - 1, 1))
            half = Z975 * sd / np.sqrt(ne)
            verdicts[d] = np.where(m - half > 0, 1, np.where(m + half < 0, -1, 0))
        out[r] = side_stat(verdicts)
    lo, hi = np.quantile(out, [0.025, 0.975])
    return float(lo), float(hi)


def rule(est, lo, hi, thr):
    return "supported" if est >= thr and lo > 0 else ("falsified" if hi < thr else "inconclusive")


def close(a, b, tol=1e-12):
    return abs(float(a) - float(b)) <= tol


# ------------------------------------------------------------------------------------------------ Study 1
CLAIMS1 = [("P1", "fixed-128", "fixed-512", 512)] + [(f"S1-{w}", f"fixed-{w}", f"fixed-{2 * w}", 2 * w) for w in (64, 128, 256)] \
    + [(f"S2-{w}", f"fixed-{w}-o25", f"fixed-{w}", w) for w in (64, 128, 256, 512)] \
    + [(f"S3-{w}", f"paragraph-{w}", f"fixed-{w}", w) for w in (64, 128, 256, 512)] \
    + [(f"S4-{w}", f"sentence-{w}", f"fixed-{w}", w) for w in (64, 128, 256, 512)]


def study1(run_dir: Path, results: dict, checks: list, post: dict) -> None:
    run = load_run(run_dir)
    by = {c[0]: c for c in CLAIMS1}
    # verdict shares, every claim x protocol x dataset
    n_bad = n_tot = 0
    vcache = {}
    for cid, a, b, wmax in CLAIMS1:
        for prot in ("count", "budget"):
            vs = []
            for d in DATASETS:
                v, lo, hi, mean, p = percentile_verdicts(diffs(run, d, a, b, prot, wmax))
                vcache[(cid, prot, d)] = (v, lo, hi, mean, p)
                vs.append(v)
                st = results["verdict_shares"][cid][prot]["by_dataset"][d]
                n_tot += 3
                n_bad += (not close(st["support_A"], (v == 1).mean())) + (not close(st["support_B"], (v == -1).mean())) \
                    + (not close(st["mean_delta"], mean.mean(), 1e-6))
            s = shares(vs)
            st = results["verdict_shares"][cid][prot]
            n_tot += 3
            n_bad += (not close(st["support_A"], s["A"])) + (not close(st["support_B"], s["B"])) + (st["n_universes"] != s["n"])
    checks.append(("Study 1 verdict shares (21 claims x 2 protocols x 4 datasets + pooled)", n_bad == 0,
                   f"{n_tot} quantities compared, {n_bad} mismatches"))
    # H1 / H1b point estimates and CIs (joint bootstrap, independent implementation)
    for h, cid, side, thr, sign in (("H1", "P1", -1, 0.20, 1), ("H1b", "S3-256", 1, 0.10, -1)):
        _, a, b, wmax = by[cid]
        blocks = {d: np.hstack([diffs(run, d, a, b, "count", wmax), diffs(run, d, a, b, "budget", wmax)]) for d in DATASETS}
        split = {d: diffs(run, d, a, b, "count", wmax).shape[1] for d in DATASETS}

        def stat(v, side=side, split=split):
            vc = np.concatenate([v[d][: split[d]] for d in DATASETS])
            vb = np.concatenate([v[d][split[d]:] for d in DATASETS])
            return float((vc == side).mean() - (vb == side).mean())

        key = "A" if side == 1 else "B"
        est = shares([vcache[(cid, "count", d)][0] for d in DATASETS])[key] - \
            shares([vcache[(cid, "budget", d)][0] for d in DATASETS])[key]
        lo, hi = joint_share_ci(blocks, stat)
        est, lo, hi = sign * est, *(sorted([sign * lo, sign * hi]))
        r = results[h]
        ok = close(r["estimate"], est) and close(r["ci95"][0], lo) and close(r["ci95"][1], hi) and r["verdict"] == rule(est, lo, hi, thr)
        checks.append((f"Study 1 {h}: estimate, joint-bootstrap CI and verdict rule", ok,
                       f"independent {100 * est:.1f} pp [{100 * lo:.1f}, {100 * hi:.1f}] -> {rule(est, lo, hi, thr)}; stored "
                       f"{100 * r['estimate']:.1f} [{100 * r['ci95'][0]:.1f}, {100 * r['ci95'][1]:.1f}] {r['verdict']}"))
    # H2 eta^2 by OLS (statsmodels, type II) on the universe means
    import pandas as pd
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    _, a, b, wmax = by["S3-256"]
    rows = []
    for d in DATASETS:
        cfg = run[d]["cfg"]
        mean = diffs(run, d, a, b, "budget", wmax).mean(axis=0)
        labs = [(r_, cfg["ops"][o], m) for r_ in cfg["retrievers"] for o in op_cols(cfg, "budget", wmax) for m in cfg["metrics"]]
        rows += [{"y": float(y), "dataset": d, "retriever": r_, "budget": o, "metric": m} for y, (r_, o, m) in zip(mean, labs)]
    df = pd.DataFrame(rows)
    tab = sm.stats.anova_lm(smf.ols("y ~ C(dataset) + C(retriever) + C(budget) + C(metric)", df).fit(), typ=2)
    total = float(((df.y - df.y.mean()) ** 2).sum())
    eta = {f: float(tab.loc[f"C({f})", "sum_sq"] / total) for f in ("dataset", "retriever", "budget", "metric")}
    ok = all(close(eta[f], results["H2"]["eta2"][f], 1e-6) for f in eta)
    checks.append(("Study 1 H2 eta^2 (statsmodels OLS type II on universe means)", ok,
                   ", ".join(f"{f} {eta[f]:.4f} (stored {results['H2']['eta2'][f]:.4f})" for f in eta)
                   + f"; dataset largest in {100 * results['H2']['dataset_largest_fraction']:.1f}% of stored replicates"))
    # H3 required n
    req, req_cluster = [], []
    for cid in [c for c in by if c.startswith(("S2", "S3"))]:
        _, a, b, wmax = by[cid]
        for d in DATASETS:
            x = diffs(run, d, a, b, "budget", wmax).astype(np.float64)
            sd = x.std(axis=0, ddof=1)
            req.append(np.ceil(((Z975 + Z80) * sd / 0.02) ** 2))
            # post-hoc: document-cluster design effect (variance of the mean with documents as clusters)
            doc = run[d]["doc"]
            dev = x - x.mean(axis=0)
            _, inv = np.unique(doc, return_inverse=True)
            csum = np.zeros((inv.max() + 1, x.shape[1]))
            np.add.at(csum, inv, dev)
            var_mean = (csum ** 2).sum(axis=0) / x.shape[0] ** 2
            sd_eff = np.sqrt(var_mean * x.shape[0])
            req_cluster.append(np.ceil(((Z975 + Z80) * sd_eff / 0.02) ** 2))
    r = np.concatenate(req)
    rc = np.concatenate(req_cluster)
    h3 = results["H3"]
    ok = close(h3["share_universes_requiring_over_500"], (r > 500).mean()) and close(h3["median_required_n"], np.median(r))
    checks.append(("Study 1 H3 required n (formula, ddof=1) and verdict rule", ok and h3["verdict"] == ("supported" if (r > 500).mean() > 0.5 else "falsified"),
                   f"{100 * (r > 500).mean():.1f}% > 500, median {np.median(r):.0f} ({len(r)} universes)"))
    post["H3_document_cluster_design_effect"] = {
        "label": "POST-HOC: required n with the per-query SD replaced by sqrt(n * Var_cluster(mean)), documents as clusters",
        "share_over_500": float((rc > 500).mean()), "median_required_n": float(np.median(rc)),
        "median_design_effect": float(np.median(rc / np.maximum(r, 1)))}
    # BH family (post-hoc): the implementation applies BH per (claim, protocol, dataset); alternative: per (claim, protocol)
    for family in ("per_dataset", "pooled_over_datasets"):
        sh = {}
        for prot in ("count", "budget"):
            vs, ps, ms = [], [], []
            for d in DATASETS:
                v, lo, hi, mean, p = vcache[("P1", prot, d)]
                if family == "per_dataset":
                    vs.append(np.where(bh(p), np.sign(mean), 0))
                else:
                    ps.append(p), ms.append(mean)
            if family != "per_dataset":
                p, mean = np.concatenate(ps), np.concatenate(ms)
                vs = [np.where(bh(p), np.sign(mean), 0)]
            sh[prot] = shares(vs)["B"]
        post.setdefault("BH_family_P1", {})[family] = sh["count"] - sh["budget"]
    stored_bh = results["H1_sensitivity"]["a_bh_fdr"]["estimate"]
    checks.append(("Study 1 sensitivity (a) BH as implemented (family = claim x protocol x dataset)",
                   close(stored_bh, post["BH_family_P1"]["per_dataset"]),
                   f"independent {100 * post['BH_family_P1']['per_dataset']:.1f} pp, stored {100 * stored_bh:.1f} pp"))
    # universe weighting (post-hoc): query-count weighting instead of equal weight per universe
    nq = {d: len(run[d]["doc"]) for d in DATASETS}
    wsum = sum(nq.values())
    sb = {prot: sum(nq[d] / wsum * (vcache[("P1", prot, d)][0] == -1).mean() for d in DATASETS) for prot in ("count", "budget")}
    post["universe_weighting_H1"] = {"equal_weight_per_universe": results["H1"]["estimate"],
                                     "query_count_weighted_datasets": sb["count"] - sb["budget"],
                                     "universes_per_dataset": {d: int(vcache[("P1", "count", d)][0].size) for d in DATASETS}}
    # Monte-Carlo seed robustness (post-hoc)
    seeds = (1, 2, 3, 4, 5)
    h1s, flips = [], 0
    for s in seeds:
        sc = shares([percentile_verdicts(diffs(run, d, "fixed-128", "fixed-512", "count", 512), seed=s)[0] for d in DATASETS])["B"]
        sbud = shares([percentile_verdicts(diffs(run, d, "fixed-128", "fixed-512", "budget", 512), seed=s)[0] for d in DATASETS])["B"]
        h1s.append(sc - sbud)
    for cid, a, b, wmax in CLAIMS1:
        for prot in ("count", "budget"):
            for d in DATASETS:
                v7 = vcache[(cid, prot, d)][0]
                v1 = percentile_verdicts(diffs(run, d, a, b, prot, wmax), seed=1)[0]
                flips += int((v7 != v1).sum())
    total_u = sum(vcache[k][0].size for k in vcache)
    post["seed_robustness"] = {"H1_estimate_seeds_1_to_5": h1s, "H1_estimate_seed_7": results["H1"]["estimate"],
                               "universe_verdicts_changed_seed7_vs_seed1": flips, "universe_verdicts_total": int(total_u)}
    # float16 margin (post-hoc): CI bounds closer to 0 than the float16 rounding bound of a mean difference
    eps = 2.0 ** -11  # max |rounding error| of a difference of two float16 values in [0, 1] is <= 2 * 2^-12
    near = sum(int(((np.abs(vcache[k][1]) < eps) | (np.abs(vcache[k][2]) < eps)).sum()) for k in vcache)
    post["float16_margin"] = {"universes_with_a_CI_bound_within_2^-11_of_zero": near, "universes_total": int(total_u)}


# ------------------------------------------------------------------------------------------------ Study 1b
def study1b_seed_sensitivity(run_dir: Path, post: dict, seeds=(1, 2, 3, 4, 5, 6, 8, 9, 10)) -> None:
    """POST-HOC: H5/H5b point estimates under other verdict-bootstrap seeds (the plan fixes seed 7)."""
    run = load_run(run_dir)
    out = {}
    for seed in (7,) + tuple(seeds):
        v = {p: [percentile_verdicts(diffs(run, d, "fixed-128", "fixed-512", p, 512, ["dense"]), seed=seed)[0]
                 for d in DATASETS] for p in ("count", "budget")}
        c, b = shares(v["count"]), shares(v["budget"])
        out[seed] = {"H5": c["B"] - b["B"], "H5b": b["A"] - c["A"], "universes_count": c["n"], "universes_budget": b["n"]}
    post["H5_seed_sensitivity"] = {"label": "POST-HOC: per-universe verdict bootstrap seed varied; seed 7 is pre-registered",
                                   "by_seed": out}


def study1b(run_dir: Path, results: dict, checks: list) -> None:
    run = load_run(run_dir)
    lengths = {d: {s["chunking"]: s["chunk_words_mean"] for s in run[d]["manifest"]["chunk_stats"]} for d in DATASETS}
    bad = 0
    for cid, arms in results["shorter_arm"].items():
        a = "semantic-bp" if cid.startswith("S5") else "semantic-cl"
        b = "fixed-" + cid.split("-")[1]
        for d in DATASETS:
            bad += arms[d] != (a if lengths[d][a] <= lengths[d][b] else b)
    checks.append(("Study 1b shorter-arm orientation from manifest chunk statistics", bad == 0, f"{bad} mismatches"))
    n_bad = n_tot = 0
    vc = {}
    for cid, sw in results["semantic_wins"].items():
        a = "semantic-bp" if cid.startswith("S5") else "semantic-cl"
        b = "fixed-" + cid.split("-")[1]
        for prot in ("count", "budget"):
            vs = [percentile_verdicts(diffs(run, d, a, b, prot, 512))[0] for d in DATASETS]
            vc[(cid, prot)] = vs
            s = shares(vs)
            n_tot += 2
            n_bad += (not close(sw[prot]["support_A"], s["A"])) + (not close(sw[prot]["support_B"], s["B"]))
    checks.append(("Study 1b semantic-arm shares (6 claims x 2 protocols)", n_bad == 0, f"{n_tot} compared, {n_bad} mismatches"))
    for h, fam, thr in (("H4", "S5", 0.20), ("H4b", "S6", 0.10)):
        sh = {}
        for prot in ("count", "budget"):
            vs = []
            for cid in [c for c in results["semantic_wins"] if c.startswith(fam)]:
                a = "semantic-bp" if fam == "S5" else "semantic-cl"
                b = "fixed-" + cid.split("-")[1]
                for i, d in enumerate(DATASETS):
                    sign = 1 if lengths[d][a] <= lengths[d][b] else -1
                    vs.append(sign * vc[(cid, prot)][i])
            sh[prot] = shares(vs)["A"]
        est = sh["budget"] - sh["count"]
        r = results[h]
        checks.append((f"Study 1b {h} point estimate and verdict rule", close(r["estimate"], est) and r["verdict"] == rule(est, *r["ci95"], thr),
                       f"independent {100 * est:.1f} pp ({100 * sh['count']:.1f}% -> {100 * sh['budget']:.1f}%); stored {100 * r['estimate']:.1f} {r['verdict']}"))
    for h, side, thr in (("H5", -1, 0.20), ("H5b", 1, 0.20)):
        vs = {p: [percentile_verdicts(diffs(run, d, "fixed-128", "fixed-512", p, 512, ["dense"]))[0] for d in DATASETS]
              for p in ("count", "budget")}
        key = "B" if side == -1 else "A"
        est = shares(vs["count"])[key] - shares(vs["budget"])[key]
        est = est if h == "H5" else -est
        r = results[h]
        checks.append((f"Study 1b {h} point estimate and verdict rule", close(r["estimate"], est) and r["verdict"] == rule(est, *r["ci95"], thr),
                       f"independent {100 * est:.1f} pp; stored {100 * r['estimate']:.1f} [{100 * r['ci95'][0]:.1f}, "
                       f"{100 * r['ci95'][1]:.1f}] {r['verdict']}"))


# ------------------------------------------------------------------------------------------------ Tier 2
def tier2(results: dict, checks: list, post: dict) -> None:
    claims = {"P1": ("fixed-128", "fixed-512"), "S3-256": ("paragraph-256", "fixed-256")}
    run = E2 / "runs" / "qwen3-4b-kaggle-gpu"
    per = {}
    for d in DATASETS:
        cells = {}
        for line in (run / d / "generations.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["status"] == "ok":
                cells[(r["qid"], r["chunking"], r["op"])] = r
        qids = sorted({k[0] for k in cells})
        per[d] = (qids, cells)
    bad = 0
    for claim, (a, b) in claims.items():
        for field in ("f1", "em", "coverage"):
            did = {}
            for d, (qids, cells) in per.items():
                val = lambda q, c, o: cells[(q, c, o)][field] if field != "coverage" else cells[(q, c, o)]["retrieval"][field]  # noqa: E731
                did[d] = np.array([(val(q, a, "budget1024") - val(q, b, "budget1024")) - (val(q, a, "count5") - val(q, b, "count5"))
                                   for q in qids])
            point = float(np.mean([did[d].mean() for d in DATASETS]))
            rng = np.random.default_rng(7)
            boot = np.zeros(2000)
            for d in sorted(did):
                x = did[d]
                boot += (rng.multinomial(len(x), np.full(len(x), 1 / len(x)), size=2000) @ x) / len(x)
            lo, hi = np.quantile(boot / 4, [0.025, 0.975])
            st = results["pooled"][claim][field]
            ok = close(st["did"], point) and close(st["lo"], lo) and close(st["hi"], hi)
            ok = ok and st["verdict"] == ("carries over" if lo > 0 else "opposite" if hi < 0 else "inconclusive")
            bad += not ok
            se = np.sqrt(sum(np.var(did[d], ddof=1) / len(did[d]) for d in DATASETS)) / 4
            post.setdefault("tier2_mde", {})[f"{claim}/{field}"] = {"stored_pooled_sd": st["mde"],
                                                                    "equal_weight_estimand": float((Z975 + Z80) * se)}
    checks.append(("Tier 2 pooled DiD, stratified bootstrap CI and reading rule (2 claims x 3 measures)", bad == 0,
                   f"{bad} mismatches; complete cases per dataset: " + ", ".join(f"{d} {len(per[d][0])}" for d in DATASETS)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args(argv)
    checks, post = [], {}
    study1(E1 / "runs/confirmatory-20261018", json.loads((E1 / "analysis/confirmatory-20261018/results.json").read_text()), checks, post)
    study1b(E3 / "runs/confirmatory-kaggle-gpu", json.loads((E3 / "analysis/confirmatory-kaggle-gpu/results.json").read_text()), checks)
    study1b_seed_sensitivity(E3 / "runs/confirmatory-kaggle-gpu", post)
    tier2(json.loads((E2 / "analysis/qwen3-4b-kaggle-gpu/results.json").read_text()), checks, post)
    Path(args.out_json).write_text(json.dumps({"checks": checks, "posthoc": post}, indent=2))
    lines = ["| Status | Check | Detail |", "|---|---|---|"]
    lines += [f"| {'PASS' if ok else 'FAIL'} | {name} | {detail} |" for name, ok, detail in checks]
    Path(args.out_md).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(json.dumps(post, indent=1))
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
