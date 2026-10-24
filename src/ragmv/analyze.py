"""Pre-registered analysis of a retrieval-multiverse run (research/preregistration.md §3-§4).

Usage:
  python -I -m ragmv.analyze --run experiments/E1_retrieval_multiverse/runs/<id> --label EXPLORATORY \
      --out <new directory> [--reps 2000] [--joint-reps 1000]

Before any statistic is computed the run is validated (`Run.validate`): every dataset manifest must have status
`ok`, a configuration whose fingerprint matches `config_sha256`, the same split, study, retriever, operating-point
and metric axes as the other datasets, unique query IDs aligned with `n_queries` and with documents of the declared
split, and NPZ arrays with the required members, shapes, dtypes and finite values in range. Axis indices are derived
from the manifest labels, never from global positions. A CONFIRMATORY or EXPLORATORY label additionally requires the
full pre-registered design (all four datasets, all chunkings and retrievers, no `max_queries`); anything less can only
be analysed with `--label SMOKE`, and the outputs then say so. Missing fields of historical manifests are reported as
`legacy_limitations`, never filled in.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import data as D
from . import stats as S
from .evaluate import METRICS
from .integrity import atomic_write_text, source_digest
from .run import BUDGETS, KS, OPS

DATASETS = ("squad2", "covidqa", "cuad", "qasper")
DEFAULT_RETRIEVER = "lucene-k1.5-b0.75-stem"
LABELS = ("EXPLORATORY", "CONFIRMATORY", "SMOKE")
SEEDS = {"verdict_bootstrap": 7, "joint_bootstrap": 11, "h2_joint_bootstrap": 13}
REQUIRED_NPZ = ("scores", "words", "rr10")


class RunValidationError(ValueError):
    """The run cannot be analysed as requested; the message lists every problem found."""


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


def parse_ops(labels: list[str]) -> list[tuple[str, int]]:
    """'k5' -> ('count', 5); 'B1024' -> ('budget', 1024)."""
    out = []
    for lab in labels:
        m = re.fullmatch(r"(k|B)(\d+)", str(lab))
        if not m:
            raise RunValidationError(f"unrecognised operating-point label {lab!r}")
        out.append(("count" if m.group(1) == "k" else "budget", int(m.group(2))))
    return out


def _config_fingerprint(config: dict) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()  # the runners' own formula


class Run:
    """Per-chunking arrays [R, n_q, ops, M] for each dataset of a run directory, loaded lazily and validated.

    `study` is "1" (ragmv.run) or "1b" (ragmv.run1b). Datasets whose manifest is absent are skipped here and reported
    by `validate`, which decides whether the label allows a partial run."""

    def __init__(self, path: Path, datasets=DATASETS, study: str = "1"):
        self.path = Path(path)
        self.study = study
        self.meta, self.cache = {}, {}
        self.missing_datasets = []
        self.problems: list[str] = []
        self.legacy: list[str] = []
        for d in datasets:
            mpath = self.path / d / "manifest.json"
            if not mpath.exists():
                self.missing_datasets.append(d)
                continue
            m = json.loads(mpath.read_text())
            if m.get("status") != "ok":
                raise RunValidationError(f"{d}: run status {m.get('status')!r}: {m.get('error')}")
            qpath = self.path / d / "queries.json"
            if not qpath.exists():
                raise RunValidationError(f"{d}: {qpath} is missing")
            q = json.loads(qpath.read_text())
            self.meta[d] = {"manifest": m, "qids": list(q.get("qids", [])), "doc_idx": np.asarray(q.get("doc_idx", []))}
        if not self.meta:
            raise FileNotFoundError(f"no dataset manifests under {self.path}")
        first = next(iter(self.meta.values()))["manifest"]["config"]
        self.retrievers = list(first["retrievers"])
        self.ops = list(first["ops"])
        self.metrics = list(first.get("metrics", METRICS))
        self.op_kinds = parse_ops(self.ops)

    @property
    def datasets(self):
        return list(self.meta)

    # ------------------------------------------------------------------------------------------- validation
    def validate(self, label: str, chunkings: list[str] | None = None, full_design: dict | None = None) -> dict:
        """Check the run before analysis; raises RunValidationError listing every problem."""
        problems, legacy = [], []
        cfgs = {d: v["manifest"]["config"] for d, v in self.meta.items()}
        splits = {d: c.get("split") for d, c in cfgs.items()}
        studies = {d: c.get("study", "1") for d, c in cfgs.items()}
        for d, c in cfgs.items():
            m = self.meta[d]["manifest"]
            if "study" not in c:
                legacy.append(f"{d}: manifest config has no 'study' field (historical Study 1 format); treated as '1'")
            if c.get("dataset", d) != d:
                problems.append(f"{d}: manifest says dataset {c.get('dataset')!r}")
            if "config_sha256" not in m:
                legacy.append(f"{d}: manifest has no config_sha256")
            elif _config_fingerprint(c) != m["config_sha256"]:
                problems.append(f"{d}: config fingerprint does not match config_sha256 (config edited after the run?)")
            for key, ref in (("retrievers", self.retrievers), ("ops", self.ops), ("metrics", self.metrics)):
                if list(c.get(key, METRICS if key == "metrics" else [])) != ref:
                    problems.append(f"{d}: {key} axis differs from the first dataset's (incompatible axes)")
            if c.get("max_queries") is not None and label != "SMOKE":
                problems.append(f"{d}: max_queries={c['max_queries']} is a smoke/partial run; use --label SMOKE")
            for field in ("n_documents", "n_queries", "chunk_stats", "versions", "platform"):
                if field not in m:
                    legacy.append(f"{d}: manifest has no {field!r}")
            if "error" not in m:
                legacy.append(f"{d}: manifest has no 'error' field")
            qids = self.meta[d]["qids"]
            doc_idx = self.meta[d]["doc_idx"]
            if len(set(qids)) != len(qids):
                problems.append(f"{d}: duplicate query IDs in queries.json ({len(qids) - len(set(qids))})")
            if len(doc_idx) != len(qids):
                problems.append(f"{d}: queries.json has {len(qids)} qids but {len(doc_idx)} doc_idx")
            if m.get("n_queries") is not None and m["n_queries"] != len(qids):
                problems.append(f"{d}: manifest n_queries {m['n_queries']} != {len(qids)} qids")
            if any(not str(q).startswith(f"{d}:") for q in qids[:1] + qids[-1:]):
                problems.append(f"{d}: query IDs are not prefixed with the dataset name")
            nd = m.get("n_documents")
            if nd is not None and len(doc_idx):
                if doc_idx.min() < 0 or doc_idx.max() >= nd:
                    problems.append(f"{d}: doc_idx outside [0, {nd})")
                elif splits[d] in ("exploratory", "confirmatory"):
                    mask = D.split_documents(int(nd), float(c.get("split_frac_exploratory", 0.2)),
                                             int(c.get("split_seed", 20261018)))
                    want = splits[d] == "exploratory"
                    wrong = int((mask[doc_idx] != want).sum())
                    if wrong:
                        problems.append(f"{d}: {wrong} queries belong to documents outside the {splits[d]} split")
        if len(set(splits.values())) > 1:
            problems.append(f"mixed splits across datasets: {splits}")
        if len(set(studies.values())) > 1 or next(iter(studies.values())) != self.study:
            problems.append(f"study mismatch: manifests say {studies}, analysis expects study {self.study!r}")
        split = next(iter(splits.values()))
        if label == "CONFIRMATORY" and split != "confirmatory":
            problems.append(f"label CONFIRMATORY but the run's split is {split!r}")
        if label == "EXPLORATORY" and split != "exploratory":
            problems.append(f"label EXPLORATORY but the run's split is {split!r}")
        if label in ("CONFIRMATORY", "EXPLORATORY"):
            if self.missing_datasets:
                problems.append(f"datasets missing for a {label} analysis: {self.missing_datasets}")
            for key, want in (full_design or {}).items():
                for d, c in cfgs.items():
                    if sorted(c.get(key, [])) != sorted(want):
                        problems.append(f"{d}: {key} {c.get(key)} is not the full pre-registered design")
            if parse_ops(self.ops) != [("count", k) for k in KS] + [("budget", b) for b in BUDGETS]:
                problems.append(f"operating points {self.ops} are not the pre-registered set {OPS}")
            if self.metrics != list(METRICS):
                problems.append(f"metrics {self.metrics} are not the pre-registered set {list(METRICS)}")
        for d, c in cfgs.items():
            for ch in chunkings or []:
                if ch not in c.get("chunkings", []):
                    problems.append(f"{d}: chunking {ch!r} required by the claims is not in the run")
                    continue
                try:
                    self.scores(d, ch)
                except RunValidationError as exc:
                    problems.append(str(exc))
        self.problems, self.legacy = problems, legacy
        if problems:
            raise RunValidationError("run validation failed:\n  - " + "\n  - ".join(problems))
        return {"label": label, "split": split, "study": self.study, "datasets": self.datasets,
                "missing_datasets": self.missing_datasets, "legacy_limitations": legacy,
                "checks": ["manifest status", "config fingerprint", "split/study consistency", "axis order",
                           "query uniqueness and alignment", "split membership of query documents",
                           "NPZ members, shapes, dtypes, finite values and ranges", "chunking availability"]}

    def _check_npz(self, dataset: str, chunking: str, z) -> np.ndarray:
        where = f"{dataset}/{chunking}.npz"
        missing = [k for k in REQUIRED_NPZ if k not in z.files]
        if "scores" in missing:
            raise RunValidationError(f"{where}: required member 'scores' is missing")
        if missing:
            self.legacy.append(f"{where}: members {missing} absent")
        n_q = len(self.meta[dataset]["qids"])
        want = (len(self.retrievers), n_q, len(self.ops), len(self.metrics))
        s = z["scores"]
        if s.shape != want:
            raise RunValidationError(f"{where}: scores shape {s.shape} != expected {want} (retrievers, queries, "
                                     "operating points, metrics) from the manifest")
        if s.dtype.kind != "f":
            raise RunValidationError(f"{where}: scores dtype {s.dtype} is not floating point")
        if not np.isfinite(s).all():
            raise RunValidationError(f"{where}: scores contain non-finite values")
        if s.min() < 0 or s.max() > 1:
            raise RunValidationError(f"{where}: scores outside [0, 1] ({s.min()}, {s.max()})")
        if "words" in z.files:
            w = z["words"]
            if w.shape != want[:3] or w.dtype.kind not in "iu" or (w < 0).any():
                raise RunValidationError(f"{where}: words array has shape {w.shape}, dtype {w.dtype} or negatives")
            for j, (kind, val) in enumerate(self.op_kinds):
                if kind == "budget" and (w[:, :, j] > val).any():
                    raise RunValidationError(f"{where}: more than {val} words retrieved at budget {val}")
        if "rr10" in z.files:
            r = z["rr10"]
            if r.shape != want[:2] or not np.isfinite(r).all() or r.min() < 0 or r.max() > 1:
                raise RunValidationError(f"{where}: rr10 has shape {r.shape} or values outside [0, 1]")
        return s

    def scores(self, dataset: str, chunking: str) -> np.ndarray:
        key = (dataset, chunking)
        if key not in self.cache:
            path = self.path / dataset / f"{chunking}.npz"
            if not path.exists():
                raise RunValidationError(f"{dataset}: {path.name} is missing")
            with np.load(path, allow_pickle=False) as z:
                self.cache[key] = self._check_npz(dataset, chunking, z).astype(np.float32)
        return self.cache[key]


def op_indices(protocol: str, wmax: int, admissible: bool = True, ops: list[str] | None = None) -> list[int]:
    """Indices of the operating points of `protocol`, derived from the run's labels (default: the runner's OPS)."""
    kinds = parse_ops(ops if ops is not None else OPS)
    if protocol == "count":
        return [i for i, (k, _) in enumerate(kinds) if k == "count"]
    return [i for i, (k, b) in enumerate(kinds) if k == "budget" and (b >= wmax or not admissible)]


def claim_diffs(run: Run, claim: Claim, protocol: str, admissible=True, retrievers=None, datasets=None):
    """Per dataset: per-query differences [n_q, U] and universe labels (retriever, op, metric)."""
    out = {}
    r_idx = [i for i, r in enumerate(run.retrievers) if retrievers is None or r in retrievers]
    if retrievers is not None and len(r_idx) != len(set(retrievers)):
        raise RunValidationError(f"retrievers {retrievers} not all in the run ({run.retrievers})")
    ops = op_indices(protocol, claim.wmax, admissible, run.ops)
    for d in datasets or run.datasets:
        delta = run.scores(d, claim.a) - run.scores(d, claim.b)  # [R, n, ops, M]
        delta = delta[r_idx][:, :, ops, :]  # [R', n, O, M]
        n = delta.shape[1]
        diff = np.moveaxis(delta, 1, 0).reshape(n, -1)
        labels = [(run.retrievers[r], run.ops[o], m) for r in r_idx for o in ops for m in run.metrics]
        out[d] = (diff, labels)
    return out


def verdict_summary(diffs, reps, seed=SEEDS["verdict_bootstrap"], clusters=None, bh=False):
    """Percentile-bootstrap verdicts per universe, pooled over datasets (every universe has equal weight).

    With `bh`, Benjamini-Hochberg is applied separately to the universes of each dataset passed in, i.e. the family
    is (claim, protocol, dataset), as implemented since the confirmatory run."""
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

    boot = S.joint_bootstrap_shares(combined, stat, reps=joint_reps, seed=SEEDS["joint_bootstrap"], clusters=clusters)
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
                             reps=joint_reps, seed=SEEDS["h2_joint_bootstrap"])
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
        elif name == "c_default_retriever" and DEFAULT_RETRIEVER not in run.retrievers:
            continue
        else:
            out = protocol_contrast(run, p1, -1, reps, joint_reps, **kw)
            sens[name] = {"estimate": out["estimate"], "ci95": out["ci95"]}
    res["H1_sensitivity"] = sens
    return res


def analysis_settings(reps: int, joint_reps: int) -> dict:
    return {"verdict_bootstrap_resamples": reps, "joint_bootstrap_replicates": joint_reps, "seeds": dict(SEEDS),
            "bh_family": "claim x protocol x dataset (BH applied to each dataset's universes separately)",
            "universe_weighting": "equal weight per universe; datasets contribute equal numbers of universes"}


def _pct(x):
    return f"{100 * x:.1f}%"


def _settings_line(res: dict) -> str:
    s = res.get("analysis_settings")
    if not s:
        return ""
    return (f"Resampling: {s['verdict_bootstrap_resamples']:,} paired percentile-bootstrap resamples per universe "
            f"(seed {s['seeds']['verdict_bootstrap']}); {s['joint_bootstrap_replicates']:,} joint query-bootstrap "
            f"replicates for share CIs (seed {s['seeds']['joint_bootstrap']}; H2 seed {s['seeds']['h2_joint_bootstrap']}).")


def label_banner(label: str) -> list[str]:
    if label == "SMOKE":
        return ["> **SMOKE / PARTIAL ANALYSIS — not a confirmatory or exploratory result.** It may cover a subset of "
                "datasets, chunkings, retrievers or queries.", ""]
    return []


def to_markdown(res: dict, label: str) -> str:
    lines = [f"# Study 1 results — {label}", ""] + label_banner(label) + [
             f"Datasets: {', '.join(res['datasets'])}; queries: " + ", ".join(f"{k} {v}" for k, v in res["n_queries"].items()), ""]
    if _settings_line(res):
        lines += [_settings_line(res), ""]
    lines += ["## Hypotheses", "", "| ID | Estimate | 95% CI | Threshold | Verdict |", "|---|---:|---|---:|---|"]
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
    if res.get("validation", {}).get("legacy_limitations"):
        lines += ["", "## Legacy limitations of the input manifests (reported, not filled in)", ""]
        lines += [f"- {x}" for x in res["validation"]["legacy_limitations"]]
    return "\n".join(lines) + "\n"


def positive_int(text: str) -> int:
    v = int(text)
    if v < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {v}")
    return v


def prepare_out(out: Path, overwrite: bool) -> None:
    if out.exists() and any(out.iterdir()) and not overwrite:
        raise SystemExit(f"{out} already contains files; analyses are written to a new directory (pass "
                         "--overwrite only for scratch output, never for committed results)")
    out.mkdir(parents=True, exist_ok=True)


def full_design_study1() -> dict:
    from .chunking import default_specs
    from .retrieval import default_retrievers

    return {"chunkings": [s.name for s in default_specs()], "retrievers": [r.name for r in default_retrievers()]}


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
        run = Run(Path(args.run))
        chunkings = sorted({x for c in preregistered_claims() for x in (c.a, c.b)})
        validation = run.validate(args.label, chunkings, full_design_study1())
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
    res["source_manifests"] = {d: {k: run.meta[d]["manifest"].get(k) for k in ("config_sha256", "started_utc")}
                               for d in run.datasets}
    atomic_write_text(out / "results.json", json.dumps(res, indent=2))
    atomic_write_text(out / "results.md", to_markdown(res, args.label))
    print((out / "results.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
