"""Paired-bootstrap inference, verdicts, joint-bootstrap uncertainty, power and eta-squared."""
from __future__ import annotations

from typing import Callable

import numpy as np

Z_975 = 1.959963984540054
Z_80 = 0.8416212335729143


def bootstrap_weights(n: int, reps: int, seed: int, clusters: np.ndarray | None = None) -> np.ndarray:
    """[reps, n] resampling weights. Query-level: multinomial counts summing to n.
    Cluster-level: clusters (e.g. documents) are drawn with replacement and every query inherits the count of
    its cluster, so rows sum to the number of queries in the resampled clusters."""
    rng = np.random.default_rng(seed)
    if clusters is None:
        return rng.multinomial(n, np.full(n, 1.0 / n), size=reps).astype(np.float32)
    ids, inv = np.unique(clusters, return_inverse=True)
    counts = rng.multinomial(len(ids), np.full(len(ids), 1.0 / len(ids)), size=reps).astype(np.float32)
    return counts[:, inv]


def paired_bootstrap_ci(diff: np.ndarray, reps: int = 2000, seed: int = 7, alpha: float = 0.05,
                        clusters: np.ndarray | None = None):
    """diff: [n_queries, n_universes]. Returns (mean, lo, hi, p_two_sided), each [n_universes]."""
    diff = np.asarray(diff, dtype=np.float32)
    w = bootstrap_weights(diff.shape[0], reps, seed, clusters)
    boot = (w @ diff) / w.sum(axis=1, keepdims=True)  # [reps, U]
    lo, hi = np.quantile(boot, [alpha / 2, 1 - alpha / 2], axis=0)
    p = np.minimum(1.0, 2 * np.minimum((boot <= 0).mean(axis=0), (boot >= 0).mean(axis=0)))
    return diff.mean(axis=0), lo, hi, p


def verdicts(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """+1 supports A (CI > 0), -1 supports B (CI < 0), 0 inconclusive."""
    return np.where(lo > 0, 1, np.where(hi < 0, -1, 0)).astype(np.int8)


def normal_verdicts(mean: np.ndarray, sd: np.ndarray, n: int) -> np.ndarray:
    half = Z_975 * sd / np.sqrt(n)
    return verdicts(mean - half, mean + half)


def bh_reject(p: np.ndarray, q: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg step-up procedure; returns a boolean rejection mask."""
    p = np.asarray(p, dtype=np.float64)
    order = np.argsort(p)
    thresh = q * np.arange(1, len(p) + 1) / len(p)
    passed = p[order] <= thresh
    k = passed.nonzero()[0].max() + 1 if passed.any() else 0
    out = np.zeros(len(p), dtype=bool)
    out[order[:k]] = True
    return out


def joint_bootstrap(diffs: dict[str, np.ndarray], fn: Callable[[dict], float], reps: int = 1000, seed: int = 11,
                    clusters: dict[str, np.ndarray] | None = None) -> np.ndarray:
    """Replicates of a statistic over universes (analysis plan §3).

    Queries (or, with `clusters`, whole documents) are resampled within each dataset; one resample per dataset is
    shared by all of its universes. `fn` receives {dataset: (mean[U], sd[U], n)} computed on the resample, where n
    is the number of queries in the resample, and returns a float.
    """
    rng = np.random.default_rng(seed)
    inv = {k: np.unique(v, return_inverse=True)[1] for k, v in clusters.items()} if clusters else {}
    out = np.empty(reps)
    for r in range(reps):
        stats = {}
        for name, d in diffs.items():
            n = d.shape[0]
            if name in inv:
                k = int(inv[name].max()) + 1
                w = rng.multinomial(k, np.full(k, 1.0 / k)).astype(np.float64)[inv[name]]
            else:
                w = rng.multinomial(n, np.full(n, 1.0 / n)).astype(np.float64)
            n_eff = float(w.sum())
            m = w @ d / n_eff
            var = np.maximum(w @ (d * d) / n_eff - m * m, 0.0) * n_eff / max(n_eff - 1, 1)
            stats[name] = (m, np.sqrt(var), n_eff)
        out[r] = fn(stats)
    return out


def joint_bootstrap_shares(diffs: dict[str, np.ndarray], select, reps: int = 1000, seed: int = 11,
                           clusters: dict[str, np.ndarray] | None = None) -> np.ndarray:
    """Like `joint_bootstrap`, but `select` receives {dataset: verdicts[U]} from normal-approximation CIs."""
    return joint_bootstrap(diffs, lambda st: select({k: normal_verdicts(*v) for k, v in st.items()}), reps, seed, clusters)


def required_n(sd: np.ndarray, delta: float = 0.02) -> np.ndarray:
    """Paired n to detect |delta| at alpha=0.05 (two-sided), power 0.8, normal approximation."""
    return np.ceil(((Z_975 + Z_80) * np.asarray(sd, dtype=np.float64) / delta) ** 2)


def eta_squared(y: np.ndarray, factors: dict[str, np.ndarray]) -> dict[str, float]:
    """Main-effect eta^2 = SS_factor / SS_total (equals type-II for a balanced full factorial)."""
    y = np.asarray(y, dtype=np.float64)
    grand = y.mean()
    ss_total = float(((y - grand) ** 2).sum())
    out = {}
    for name, levels in factors.items():
        ss = 0.0
        for lv in np.unique(levels):
            sel = levels == lv
            ss += sel.sum() * (y[sel].mean() - grand) ** 2
        out[name] = ss / ss_total if ss_total > 0 else 0.0
    return out
