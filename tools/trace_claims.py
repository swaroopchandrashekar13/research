"""Trace every result macro used in the canonical manuscript to its source and recompute it independently.

For each macro in manuscript/main.tex that numbers.tex defines, this script states the source file and JSON path,
recomputes the value without using make_numbers.py, and compares it with numbers.tex. It also lists the literal
numbers in the manuscript prose so they can be classified (design constants vs. results).

Usage: python -I tools/trace_claims.py --out docs/repair/CLAIM_TRACE_MACROS.md   (exit 1 on any mismatch/untraced)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = {"E1": "experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018/results.json",
     "E2": "experiments/E2_generation/analysis/qwen3-4b-kaggle-gpu/results.json",
     "E3": "experiments/E3_semantic_dense/analysis/confirmatory-kaggle-gpu/results.json",
     "PH1": "experiments/E1_retrieval_multiverse/analysis/posthoc-charmetric-20261024",
     "PH3": "experiments/E3_semantic_dense/analysis/posthoc-charmetric-bm25-20261024",
     "SV": "docs/repair/statistical_verification.json", "AUD": "literature/protocol_audit/coding.csv",
     "E3RUN": "experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu"}
DSN = {"squad2": "Squadtwo", "covidqa": "Covidqa", "cuad": "Cuad", "qasper": "Qasper"}
WORDS = {"128": "OneTwoEight", "256": "TwoFiveSix", "512": "FiveTwelve", "64": "SixFour"}


def j(key):
    return json.loads((ROOT / P[key]).read_text())


def pct(x):
    return f"{100 * x:.1f}"


def s3(x):
    return f"{x:+.3f}".replace("-", "\\ensuremath{-}")


def table() -> dict[str, tuple[str, str]]:
    """macro -> (value, source)"""
    e1, e2, e3 = j("E1"), j("E2"), j("E3")
    t: dict[str, tuple[str, str]] = {}

    def add(name, value, src):
        t[name] = (value, src)
    add("EoneNq", f"{sum(e1['n_queries'].values()):,}", f"{P['E1']}: sum(n_queries)")
    for d, n in e1["n_queries"].items():
        add(f"EoneNq{DSN[d]}", f"{n:,}", f"{P['E1']}: n_queries.{d}")
    for h, k in (("H1", "HOne"), ("H1b", "HOneB")):
        r = e1[h]
        add(f"{k}Est", pct(r["estimate"]), f"{P['E1']}: {h}.estimate")
        add(f"{k}Lo", pct(r["ci95"][0]), f"{P['E1']}: {h}.ci95[0]")
        add(f"{k}Hi", pct(r["ci95"][1]), f"{P['E1']}: {h}.ci95[1]")
    for h, k in (("H1", "HOne"), ("H1b", "HOneB"), ("H2", "HTwo"), ("H3", "HThree")):
        add(f"{k}Verdict", e1[h]["verdict"], f"{P['E1']}: {h}.verdict")
    p1 = e1["verdict_shares"]["P1"]
    for prot in ("count", "budget"):
        P_ = prot.capitalize()
        add(f"Pone{P_}FiveTwelve", pct(p1[prot]["support_B"]), f"{P['E1']}: verdict_shares.P1.{prot}.support_B")
        add(f"Pone{P_}OneTwoEight", pct(p1[prot]["support_A"]), f"{P['E1']}: verdict_shares.P1.{prot}.support_A")
        add(f"PoneUniverses{P_}", str(p1[prot]["n_universes"]), f"{P['E1']}: verdict_shares.P1.{prot}.n_universes")
    for cid in ("S2-128", "S2-256", "S1-128", "S1-64"):
        fam, w = cid.split("-")
        base = {"S2": "Stwo", "S1": "Sone"}[fam] + WORDS[w]
        for prot in ("count", "budget"):
            for side, key in (("A", "support_A"), ("B", "support_B")):
                add(f"{base}{prot.capitalize()}{side}", pct(e1["verdict_shares"][cid][prot][key]),
                    f"{P['E1']}: verdict_shares.{cid}.{prot}.{key}")
    add("HTwoDatasetEta", f"{e1['H2']['eta2']['dataset']:.2f}", f"{P['E1']}: H2.eta2.dataset")
    add("HTwoRetrieverEta", f"{e1['H2']['eta2']['retriever']:.2f}", f"{P['E1']}: H2.eta2.retriever")
    add("HTwoFraction", pct(e1["H2"]["dataset_largest_fraction"]), f"{P['E1']}: H2.dataset_largest_fraction")
    add("HThreeShare", pct(e1["H3"]["share_universes_requiring_over_500"]), f"{P['E1']}: H3.share_universes_requiring_over_500")
    add("HThreeMedianN", f"{e1['H3']['median_required_n']:,.0f}", f"{P['E1']}: H3.median_required_n")
    for k, key in (("b_without_squad2", "SensNoSquad"), ("c_default_retriever", "SensDefRet"), ("d_cluster_bootstrap", "SensCluster"),
                   ("e_all_budgets", "SensAllBudgets"), ("a_bh_fdr", "SensBH")):
        r = e1["H1_sensitivity"][k]
        add(f"{key}Est", pct(r["estimate"]), f"{P['E1']}: H1_sensitivity.{k}.estimate")
        if "ci95" in r:
            add(f"{key}Lo", pct(r["ci95"][0]), f"{P['E1']}: H1_sensitivity.{k}.ci95[0]")
            add(f"{key}Hi", pct(r["ci95"][1]), f"{P['E1']}: H1_sensitivity.{k}.ci95[1]")
    for c, key in (("P1", "Pone"), ("S3-256", "Sthree")):
        for meas, mk in (("f1", "Fone"), ("em", "Em"), ("coverage", "Cov")):
            r = e2["pooled"][c][meas]
            add(f"Etwo{key}{mk}", s3(r["did"]), f"{P['E2']}: pooled.{c}.{meas}.did")
            add(f"Etwo{key}{mk}Lo", s3(r["lo"]), f"{P['E2']}: pooled.{c}.{meas}.lo")
            add(f"Etwo{key}{mk}Hi", s3(r["hi"]), f"{P['E2']}: pooled.{c}.{meas}.hi")
            add(f"Etwo{key}{mk}Mde", f"{r['mde']:.3f}", f"{P['E2']}: pooled.{c}.{meas}.mde")
    for d, key in (("cuad", "Cuad"), ("qasper", "Qasper")):
        g = e2["datasets"][d]["diagnostics"]
        add(f"EtwoTrunc{key}", str(g["finish_reasons"].get("length", 0)), f"{P['E2']}: datasets.{d}.diagnostics.finish_reasons.length")
        add(f"EtwoJobs{key}", str(g["rows_total"]), f"{P['E2']}: datasets.{d}.diagnostics.rows_total")
    for arm, ak in (("fixed-128", "OneTwoEight"), ("fixed-512", "FiveTwelve")):
        for op, ok in (("count5", "Count"), ("budget1024", "Budget")):
            vals = [e2["datasets"][d]["means"][f"{arm}|{op}"]["em"] for d in e2["datasets"]]
            add(f"EtwoEm{ak}{ok}", f"{sum(vals) / len(vals):.3f}", f"{P['E2']}: mean over datasets of means['{arm}|{op}'].em")
    for arm, key in (("fixed-512", "FiveTwelve"), ("fixed-128", "OneTwoEight")):
        for f, fk in (("f1", "Fone"), ("coverage", "Cov")):
            add(f"EtwoSquad{key}Budget{fk}", f"{e2['datasets']['squad2']['means'][arm + '|budget1024'][f]:.2f}",
                f"{P['E2']}: datasets.squad2.means['{arm}|budget1024'].{f}")
    for h, key in (("H4", "HFour"), ("H4b", "HFourB"), ("H5", "HFive"), ("H5b", "HFiveB")):
        r = e3[h]
        add(f"{key}Est", pct(r["estimate"]), f"{P['E3']}: {h}.estimate")
        add(f"{key}Lo", pct(r["ci95"][0]), f"{P['E3']}: {h}.ci95[0]")
        add(f"{key}Hi", pct(r["ci95"][1]), f"{P['E3']}: {h}.ci95[1]")
        add(f"{key}Verdict", r["verdict"], f"{P['E3']}: {h}.verdict")
    for h, key in (("H4", "HFour"), ("H4b", "HFourB"), ("H5b", "HFiveB")):
        add(f"{key}Count", pct(e3[h]["count_share"]), f"{P['E3']}: {h}.count_share")
        add(f"{key}Budget", pct(e3[h]["budget_share"]), f"{P['E3']}: {h}.budget_share")
    sw = e3["semantic_wins"]["S5-128"]
    for prot in ("count", "budget"):
        add(f"SfiveOneTwoEight{prot.capitalize()}Sem", pct(sw[prot]["support_A"]), f"{P['E3']}: semantic_wins.S5-128.{prot}.support_A")
        add(f"SfiveOneTwoEight{prot.capitalize()}Fix", pct(sw[prot]["support_B"]), f"{P['E3']}: semantic_wins.S5-128.{prot}.support_B")
        add(f"SfiveUniverses{prot.capitalize()}", str(sw[prot]["n_universes"]), f"{P['E3']}: semantic_wins.S5-128.{prot}.n_universes")
        add(f"PoneDenseUniverses{prot.capitalize()}", str(e3["H5"][prot]["n_universes"]), f"{P['E3']}: H5.{prot}.n_universes")
        add(f"HFive{prot.capitalize()}FiveTwelve", pct(e3["H5"][prot]["support_B"]), f"{P['E3']}: H5.{prot}.support_B")
    for k, key in (("f_bm25_only", "HFourBmOnly"), ("f_dense_only", "HFourDenseOnly")):
        r = e3["H4_sensitivity"][k]
        add(f"{key}Est", pct(r["estimate"]), f"{P['E3']}: H4_sensitivity.{k}.estimate")
    for c, key in (("semantic-bp", "SemBp"), ("semantic-cl", "SemCl")):
        lens = [e3["mean_chunk_words"][d][c] for d in e3["mean_chunk_words"]]
        add(f"{key}Min", f"{min(lens):.0f}", f"{P['E3']}: min over datasets of mean_chunk_words.*.{c}")
        add(f"{key}Max", f"{max(lens):.0f}", f"{P['E3']}: max over datasets of mean_chunk_words.*.{c}")
    nc = [s["noncontiguous_share"] for d in e3["datasets"] for s in
          json.loads((ROOT / P["E3RUN"] / d / "manifest.json").read_text())["chunk_stats"] if s["chunking"] == "semantic-cl"]
    add("SemClNoncontigMin", pct(min(nc)), f"{P['E3RUN']}/*/manifest.json: min chunk_stats[semantic-cl].noncontiguous_share")
    rows = [r for r in csv.DictReader(open(ROOT / P["AUD"])) if r["included"] == "yes"]
    sys.path.insert(0, str((ROOT / P["AUD"]).parent))
    from analyze_audit import exposure
    n = len(rows)
    ex = sum(exposure(r).startswith("exposed") for r in rows)
    z = 1.959963984540054
    p = ex / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    add("AuditN", str(n), f"{P['AUD']}: rows with included=yes")
    add("AuditFixedK", str(sum(r["selection_protocol"] == "fixed_k" for r in rows)), f"{P['AUD']}: selection_protocol=fixed_k")
    add("AuditBudget", str(sum(r["selection_protocol"] in ("fixed_budget", "both") for r in rows)), f"{P['AUD']}: selection_protocol in fixed_budget/both")
    add("AuditUncertainty", str(sum(r["uncertainty_reported"] in ("CI", "significance_test") for r in rows)), f"{P['AUD']}: uncertainty_reported in CI/test")
    add("AuditExposed", str(ex), f"{P['AUD']}: exposure() starts with 'exposed'")
    add("AuditExposedPct", pct(p), "AuditExposed / AuditN")
    add("AuditExposedLo", pct(c - h), "Wilson 95% lower bound")
    add("AuditExposedHi", pct(c + h), "Wilson 95% upper bound")
    sv = j("SV")["posthoc"]
    add("SensBHPooledEst", pct(sv["BH_family_P1"]["pooled_over_datasets"]), f"{P['SV']}: posthoc.BH_family_P1.pooled_over_datasets (POST-HOC)")
    add("EtwoPoneFoneMdeStrat", f"{sv['tier2_mde']['P1/f1']['equal_weight_estimand']:.3f}", f"{P['SV']}: posthoc.tier2_mde['P1/f1'] (POST-HOC)")
    for key, d in (("PosthocEquivElements", "PH1"), ("PosthocEquivElementsB", "PH3")):
        rep = json.loads((ROOT / P[d] / "selection_equivalence.json").read_text())
        tot = sum(v["elements_scores"] + v["elements_words"] for ds, cs in rep.items() if not ds.startswith("_")
                  for ch, v in cs.items() if not ch.startswith("_"))
        add(key, f"{tot:,}", f"{P[d]}/selection_equivalence.json: sum of compared elements (POST-HOC)")
    fl = json.loads((ROOT / P["PH1"] / "summary.json").read_text())["universe_verdict_changes_vs_stored"]["char"]
    add("PosthocCharFlips", f"{fl['changed']:,}", f"{P['PH1']}/summary.json: universe_verdict_changes_vs_stored.char.changed (POST-HOC)")
    add("PosthocUniverses", f"{fl['total']:,}", f"{P['PH1']}/summary.json: ...char.total (POST-HOC)")
    return t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    tex = (ROOT / "manuscript/main.tex").read_text()
    nums = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{((?:[^{}]|\{[^{}]*\})*)\}", (ROOT / "manuscript/numbers.tex").read_text()))
    used = sorted(set(re.findall(r"\\([A-Z][A-Za-z]+)", tex)) & set(nums))
    t = table()
    bad = 0
    lines = ["# Macro trace (generated by tools/trace_claims.py)", "",
             "Each result macro used in `manuscript/main.tex`, its value in `numbers.tex`, the source, and an independent "
             "recomputation (not using `make_numbers.py`).", "", "| Macro | numbers.tex | Recomputed | Source |", "|---|---|---|---|"]
    for k in used:
        v, src = t.get(k, ("UNTRACED", "—"))
        ok = v == nums[k]
        bad += not ok
        lines.append(f"| `\\{k}` | {nums[k]} | {v}{'' if ok else ' **MISMATCH**'} | {src} |")
    lines.append(f"\n{len(used)} macros used; {len(used) - bad} recomputed identically; {bad} mismatched or untraced.")
    (ROOT / args.out).write_text("\n".join(lines) + "\n")
    print(lines[-1])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
