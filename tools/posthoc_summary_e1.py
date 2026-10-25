"""POST-HOC (2026-10-24): summarise the Study 1 character-metric sensitivity and count universe verdict changes.

Usage: python -I tools/posthoc_summary_e1.py WORKDIR OUT.json
WORKDIR holds posthoc/e1_confirmatory/<variant>/ (from `python -I -m ragmv.posthoc study1 ... --out
WORKDIR/posthoc/e1_confirmatory`) and posthoc/e1_analysis_<variant>/ (from `python -I -m ragmv.analyze --label POSTHOC`).
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import independent_stats as IS
ap = argparse.ArgumentParser(description="Summarise the Study 1 character-metric sensitivity.")
ap.add_argument("workdir", type=Path); ap.add_argument("out", type=Path)
args = ap.parse_args(); sp, out = args.workdir, args.out
stored = json.loads((ROOT / "experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018/results.json").read_text())
res = {"stored (word, float16)": stored}
for v in ("word64", "char", "char_nows"):
    res[v] = json.loads((sp / f"posthoc/e1_analysis_{v}/results.json").read_text())
def pp(x): return f"{100*x:.1f}"
rows = []
for name, r in res.items():
    p1 = r["verdict_shares"]["P1"]
    rows.append({"variant": name,
        "H1": f"{pp(r['H1']['estimate'])} [{pp(r['H1']['ci95'][0])}, {pp(r['H1']['ci95'][1])}] {r['H1']['verdict']}",
        "H1b": f"{pp(r['H1b']['estimate'])} [{pp(r['H1b']['ci95'][0])}, {pp(r['H1b']['ci95'][1])}] {r['H1b']['verdict']}",
        "H2": f"eta2 dataset {r['H2']['eta2']['dataset']:.3f}; largest {pp(r['H2']['dataset_largest_fraction'])}% {r['H2']['verdict']}",
        "H3": f"{pp(r['H3']['share_universes_requiring_over_500'])}% (median {r['H3']['median_required_n']:.0f}) {r['H3']['verdict']}",
        "P1 count 512/128": f"{pp(p1['count']['support_B'])}/{pp(p1['count']['support_A'])}",
        "P1 budget 512/128": f"{pp(p1['budget']['support_B'])}/{pp(p1['budget']['support_A'])}",
        "sens": ", ".join(f"{k.split('_')[0]} {pp(s['estimate'])}" for k, s in r["H1_sensitivity"].items())})
# universe-level verdict changes vs stored
runs = {"stored": IS.load_run(ROOT / "experiments/E1_retrieval_multiverse/runs/confirmatory-20261018")}
for v in ("word64", "char", "char_nows"):
    runs[v] = IS.load_run(sp / f"posthoc/e1_confirmatory/{v}")
flips = {v: {"total": 0, "changed": 0, "to_inconclusive": 0, "from_inconclusive": 0, "sign_reversal": 0} for v in ("word64", "char", "char_nows")}
per_metric = {v: {} for v in flips}
for cid, a, b, wmax in IS.CLAIMS1:
    for prot in ("count", "budget"):
        for d in IS.DATASETS:
            v0 = IS.percentile_verdicts(IS.diffs(runs["stored"], d, a, b, prot, wmax))[0]
            for v in flips:
                v1 = IS.percentile_verdicts(IS.diffs(runs[v], d, a, b, prot, wmax))[0]
                f = flips[v]
                f["total"] += v0.size; ch = v0 != v1
                f["changed"] += int(ch.sum()); f["to_inconclusive"] += int(((v1 == 0) & ch).sum())
                f["from_inconclusive"] += int(((v0 == 0) & ch).sum()); f["sign_reversal"] += int((v0 * v1 == -1).sum())
                mets = np.tile(np.array([0, 1, 2]), v0.size // 3)
                for mi, mn in enumerate(("hit_strict", "hit_lenient", "coverage")):
                    pm = per_metric[v].setdefault(mn, [0, 0]); pm[0] += int(ch[mets == mi].sum()); pm[1] += int((mets == mi).sum())
summary = {"rows": rows, "universe_verdict_changes_vs_stored": flips, "changes_by_metric": per_metric}
out.write_text(json.dumps(summary, indent=1))
for r in rows: print(r)
print(json.dumps(flips, indent=1)); print(json.dumps(per_metric))
