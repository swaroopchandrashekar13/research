"""Generate numbers.tex: the paper's result numbers as LaTeX macros, read from the logged result files.

Usage: python -I manuscript/make_numbers.py [--e1 results.json] [--e2 results.json] [--e3 results.json]
                                           [--e3-run RUN_DIR] [--audit coding.csv] [--out numbers.tex]
Defaults are the repository's analysed results and manuscript/numbers.tex. Design constants (dataset names, grid
sizes, seeds, thresholds) are written literally in the manuscript; result values come from these macros.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E1 = ROOT / "experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018/results.json"
E2 = ROOT / "experiments/E2_generation/analysis/qwen3-4b-kaggle-gpu/results.json"
E3 = ROOT / "experiments/E3_semantic_dense/analysis/confirmatory-kaggle-gpu/results.json"
E3RUN = ROOT / "experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu"
E3PILOT = ROOT / "experiments/E3_semantic_dense/analysis/exploratory-kaggle-gpu/results.json"
AUDIT = ROOT / "literature/protocol_audit/coding.csv"
OUT = ROOT / "manuscript" / "numbers.tex"
POSTHOC_E1 = ROOT / "experiments/E1_retrieval_multiverse/analysis/posthoc-charmetric-20261024"
POSTHOC_E3 = ROOT / "experiments/E3_semantic_dense/analysis/posthoc-charmetric-bm25-20261024"
STATVER = ROOT / "docs/remediation/statistical_verification.json"
UNDERFILL = ROOT / "docs/remediation/underfill_bound.json"


def equivalence_elements(path: Path) -> tuple[int, int]:
    rep = json.loads(path.read_text())
    n = bad = 0
    for d, cs in rep.items():
        if d.startswith("_"):
            continue
        for c, v in cs.items():
            if not c.startswith("_"):
                n += v["elements_scores"] + v["elements_words"]
                bad += v["mismatch_scores"] + v["mismatch_words"]
    return n, bad


def pp(x: float) -> str:  # proportion -> percentage points / percent, one decimal
    return f"{100 * x:.1f}"


def f3(x: float) -> str:  # typeset minus sign (macros are used in running text)
    return f"{x:+.3f}".replace("-", "\\ensuremath{-}")


def wilson(k: int, n: int, z: float = 1.959963984540054):
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--e1", type=Path, default=E1)
    ap.add_argument("--e2", type=Path, default=E2)
    ap.add_argument("--e3", type=Path, default=E3)
    ap.add_argument("--e3-run", type=Path, default=E3RUN)
    ap.add_argument("--e3-pilot", type=Path, default=E3PILOT)
    ap.add_argument("--audit", type=Path, default=AUDIT)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--posthoc-e1", type=Path, default=POSTHOC_E1)
    ap.add_argument("--posthoc-e3", type=Path, default=POSTHOC_E3)
    ap.add_argument("--stat-verification", type=Path, default=STATVER)
    ap.add_argument("--underfill-bound", type=Path, default=UNDERFILL)
    args = ap.parse_args(argv)
    m: dict[str, str] = {}
    e1 = json.loads(args.e1.read_text())
    m["EoneNq"] = f"{sum(e1['n_queries'].values()):,}"
    for d, n in e1["n_queries"].items():
        m[f"EoneNq{d.replace('2', 'two').capitalize()}"] = f"{n:,}"
    for h, key in (("H1", "HOne"), ("H1b", "HOneB")):
        r = e1[h]
        m[f"{key}Est"], m[f"{key}Lo"], m[f"{key}Hi"] = pp(r["estimate"]), pp(r["ci95"][0]), pp(r["ci95"][1])
    p1 = e1["verdict_shares"]["P1"]
    m["PoneCountFiveTwelve"], m["PoneCountOneTwoEight"] = pp(p1["count"]["support_B"]), pp(p1["count"]["support_A"])
    m["PoneBudgetFiveTwelve"], m["PoneBudgetOneTwoEight"] = pp(p1["budget"]["support_B"]), pp(p1["budget"]["support_A"])
    m["PoneUniversesCount"], m["PoneUniversesBudget"] = str(p1["count"]["n_universes"]), str(p1["budget"]["n_universes"])
    for cid, key in (("S2-128", "StwoOneTwoEight"), ("S2-256", "StwoTwoFiveSix"), ("S1-128", "SoneOneTwoEight")):
        v = e1["verdict_shares"][cid]  # S2 compares equal-length arms: the built-in control for the mechanism
        for prot in ("count", "budget"):
            m[f"{key}{prot.capitalize()}A"], m[f"{key}{prot.capitalize()}B"] = pp(v[prot]["support_A"]), pp(v[prot]["support_B"])
    m["HTwoDatasetEta"] = f"{e1['H2']['eta2']['dataset']:.2f}"
    m["HTwoRetrieverEta"] = f"{e1['H2']['eta2']['retriever']:.2f}"
    m["HTwoFraction"] = pp(e1["H2"]["dataset_largest_fraction"])
    for h, key in (("H1", "HOne"), ("H1b", "HOneB"), ("H2", "HTwo"), ("H3", "HThree")):
        m[f"{key}Verdict"] = e1[h]["verdict"]
    m["HThreeShare"], m["HThreeMedianN"] = pp(e1["H3"]["share_universes_requiring_over_500"]), f"{e1['H3']['median_required_n']:,.0f}"
    for k, key in (("b_without_squad2", "SensNoSquad"), ("c_default_retriever", "SensDefRet"),
                   ("d_cluster_bootstrap", "SensCluster"), ("e_all_budgets", "SensAllBudgets"), ("a_bh_fdr", "SensBH")):
        r = e1["H1_sensitivity"][k]
        m[f"{key}Est"] = pp(r["estimate"])
        if "ci95" in r:
            m[f"{key}Lo"], m[f"{key}Hi"] = pp(r["ci95"][0]), pp(r["ci95"][1])

    e2 = json.loads(args.e2.read_text())
    for c, key in (("P1", "Pone"), ("S3-256", "Sthree")):
        for meas, mk in (("f1", "Fone"), ("em", "Em"), ("coverage", "Cov")):
            r = e2["pooled"][c][meas]
            m[f"Etwo{key}{mk}"], m[f"Etwo{key}{mk}Lo"], m[f"Etwo{key}{mk}Hi"] = f3(r["did"]), f3(r["lo"]), f3(r["hi"])
            m[f"Etwo{key}{mk}Mde"] = f"{r['mde']:.3f}"

    e3 = json.loads(args.e3.read_text())
    for h, key in (("H4", "HFour"), ("H4b", "HFourB"), ("H5", "HFive"), ("H5b", "HFiveB")):
        r = e3[h]
        m[f"{key}Est"], m[f"{key}Lo"], m[f"{key}Hi"] = pp(r["estimate"]), pp(r["ci95"][0]), pp(r["ci95"][1])
        m[f"{key}Verdict"] = r["verdict"]
    for h, key in (("H4", "HFour"), ("H4b", "HFourB"), ("H5b", "HFiveB")):
        m[f"{key}Count"], m[f"{key}Budget"] = pp(e3[h]["count_share"]), pp(e3[h]["budget_share"])
    sw = e3["semantic_wins"]["S5-128"]
    m["SfiveOneTwoEightCountSem"], m["SfiveOneTwoEightCountFix"] = pp(sw["count"]["support_A"]), pp(sw["count"]["support_B"])
    m["SfiveOneTwoEightBudgetSem"], m["SfiveOneTwoEightBudgetFix"] = pp(sw["budget"]["support_A"]), pp(sw["budget"]["support_B"])
    for k, key in (("f_bm25_only", "HFourBmOnly"), ("f_dense_only", "HFourDenseOnly")):
        r = e3["H4_sensitivity"][k]
        m[f"{key}Est"], m[f"{key}Lo"], m[f"{key}Hi"] = pp(r["estimate"]), pp(r["ci95"][0]), pp(r["ci95"][1])
        m[f"{key}Count"], m[f"{key}Budget"] = pp(r["count_share"]), pp(r["budget_share"])
    m["HFiveCountFiveTwelve"], m["HFiveBudgetFiveTwelve"] = pp(e3["H5"]["count"]["support_B"]), pp(e3["H5"]["budget"]["support_B"])
    e3p = json.loads(args.e3_pilot.read_text())  # exploratory pilot: the observations behind the H5b amendment
    m["HFiveBPilotCount"], m["HFiveBPilotBudget"] = pp(e3p["H5b"]["count_share"]), pp(e3p["H5b"]["budget_share"])
    m["HFivePilotCountFiveTwelve"] = pp(e3p["H5"]["count"]["support_B"])
    for c, key in (("semantic-bp", "SemBp"), ("semantic-cl", "SemCl")):
        lens = [e3["mean_chunk_words"][d][c] for d in e3["mean_chunk_words"]]
        m[f"{key}Min"], m[f"{key}Max"] = f"{min(lens):.0f}", f"{max(lens):.0f}"
    run3 = args.e3_run
    nc = [s["noncontiguous_share"] for d in e3["datasets"]
          for s in json.loads((run3 / d / "manifest.json").read_text())["chunk_stats"] if s["chunking"] == "semantic-cl"]
    m["SemClNoncontigMin"] = pp(min(nc))
    sw5 = e3["semantic_wins"]["S5-128"]  # universes per S5/S6 contrast (both retrievers) and for dense-only P1
    m["SfiveUniversesCount"], m["SfiveUniversesBudget"] = str(sw5["count"]["n_universes"]), str(sw5["budget"]["n_universes"])
    m["PoneDenseUniversesCount"], m["PoneDenseUniversesBudget"] = (str(e3["H5"]["count"]["n_universes"]),
                                                                   str(e3["H5"]["budget"]["n_universes"]))
    for d, key in (("cuad", "Cuad"), ("qasper", "Qasper")):
        g = e2["datasets"][d]["diagnostics"]
        m[f"EtwoTrunc{key}"], m[f"EtwoJobs{key}"] = str(g["finish_reasons"].get("length", 0)), str(g["rows_total"])
    for arm, ak in (("fixed-128", "OneTwoEight"), ("fixed-512", "FiveTwelve")):  # pooled (equal-weight) EM cell means
        for op, ok in (("count5", "Count"), ("budget1024", "Budget")):
            vals = [e2["datasets"][d]["means"][f"{arm}|{op}"]["em"] for d in e2["datasets"]]
            m[f"EtwoEm{ak}{ok}"] = f"{sum(vals) / len(vals):.3f}"
    v = e1["verdict_shares"]["S1-64"]
    m["SoneSixFourBudgetA"], m["SoneSixFourBudgetB"] = pp(v["budget"]["support_A"]), pp(v["budget"]["support_B"])
    m["SoneSixFourCountB"] = pp(v["count"]["support_B"])
    sq = e2["datasets"]["squad2"]["means"]  # exploratory observation (E2 RESULTS.md), not a planned estimate
    for arm, key in (("fixed-512", "FiveTwelve"), ("fixed-128", "OneTwoEight")):
        m[f"EtwoSquad{key}BudgetFone"] = f"{sq[arm + '|budget1024']['f1']:.2f}"
        m[f"EtwoSquad{key}BudgetCov"] = f"{sq[arm + '|budget1024']['coverage']:.2f}"

    rows = [r for r in csv.DictReader(open(args.audit)) if r["included"] == "yes"]
    n = len(rows)
    fixed_k = sum(r["selection_protocol"] == "fixed_k" for r in rows)
    budget = sum(r["selection_protocol"] in ("fixed_budget", "both") for r in rows)
    unc = sum(r["uncertainty_reported"] in ("CI", "significance_test") for r in rows)
    m["AuditN"], m["AuditFixedK"], m["AuditBudget"], m["AuditUncertainty"] = str(n), str(fixed_k), str(budget), str(unc)
    import sys
    sys.path.insert(0, str(args.audit.parent))
    from analyze_audit import exposure  # the audit's own rules, not a re-implementation
    exposed = sum(exposure(r).startswith("exposed") for r in rows)
    lo, hi = wilson(exposed, n)
    m["AuditExposed"], m["AuditExposedPct"], m["AuditExposedLo"], m["AuditExposedHi"] = str(exposed), pp(exposed / n), pp(lo), pp(hi)

    # post-hoc checks (labelled as such in the text)
    ver = json.loads(args.stat_verification.read_text())["posthoc"]
    m["SensBHPooledEst"] = pp(ver["BH_family_P1"]["pooled_over_datasets"])
    h5 = [v["H5"] for s, v in ver["H5_seed_sensitivity"]["by_seed"].items() if s != "7"]
    m["HFiveSeedMin"], m["HFiveSeedMax"], m["HFiveSeedN"] = pp(min(h5)), pp(max(h5)), str(len(h5))
    m["EtwoPoneFoneMdeStrat"] = f"{ver['tier2_mde']['P1/f1']['equal_weight_estimand']:.3f}"
    for key, path in (("PosthocEquivElements", args.posthoc_e1), ("PosthocEquivElementsB", args.posthoc_e3)):
        n, bad = equivalence_elements(path / "selection_equivalence.json")
        if bad:
            raise SystemExit(f"{path}: stored scores/word counts not reproduced ({bad} mismatches); post-hoc numbers not usable")
        m[key] = f"{n:,}"
    normal = ver["normal_verdict_point_estimates"]["estimates"]
    m["HFiveNormalEst"] = pp(normal["H5"])
    planned = {"H1": e1["H1"], "H1b": e1["H1b"], "H4": e3["H4"], "H4b": e3["H4b"], "H5b": e3["H5b"]}
    m["NormalGapMaxOther"] = pp(max(abs(normal[h] - r["estimate"]) for h, r in planned.items()))
    ub = json.loads(args.underfill_bound.read_text())
    cells = sorted(ub["cells"], key=lambda c: c["chunking"])
    m["UnderfillCells"] = str(len(cells))
    m["UnderfillWordsA"], m["UnderfillWordsB"] = (f"{c['words']:,}" for c in cells)
    run = ub["runs"]["confirmatory-kaggle-gpu"]
    if run["verdict_changes"]:
        raise SystemExit("underfill bound changes a verdict; the manuscript text must be revised")
    h4 = {f["field"]: f["upper_bound"] for f in run["changed_fields"]}["H4.estimate"]
    m["UnderfillHFourMax"] = pp(h4)
    m["UnderfillHFourDelta"] = pp(h4 - e3["H4"]["estimate"])
    flips = json.loads((args.posthoc_e1 / "summary.json").read_text())["universe_verdict_changes_vs_stored"]
    m["PosthocCharFlips"], m["PosthocUniverses"] = f"{flips['char']['changed']:,}", f"{flips['char']['total']:,}"
    out = ["% Generated by manuscript/make_numbers.py from logged results. Do not edit by hand."]
    out += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(m.items())]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out) + "\n")
    print(f"{len(m)} macros written to {args.out}")


if __name__ == "__main__":
    main()
