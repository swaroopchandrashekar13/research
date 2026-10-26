"""POST-HOC (2026-10-24): Study 1b BM25-arm quantities (H4/H4b/P1 in BM25-only form) for the stored word metric
and the character-metric variants on re-executed BM25 selections. Dense retrieval is not covered.

Usage: python -I tools/posthoc_summary_e3_bm25.py WORKDIR   (reads WORKDIR/posthoc/e3_confirmatory_bm25/<variant>,
writes WORKDIR/logs/posthoc_summary_e3_bm25.json)
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ragmv import analyze as A, analyze1b as B
ap = argparse.ArgumentParser(description="Study 1b BM25-arm quantities for the character-metric variants.")
ap.add_argument("workdir", type=Path)
sp = ap.parse_args().workdir
def quantities(run, retr):
    lengths = B.mean_lengths(run)
    claims = B.study1b_claims()
    out = {}
    for h, fam, thr in (("H4_bm25", "S5", 0.20), ("H4b_bm25", "S6", 0.10), ("P1_shorter_bm25", "P1", 0.20)):
        r = B.shorter_contrast(run, claims[fam], lengths, 2000, 1000, retrievers=retr)
        r["verdict_rule_at_threshold"] = A.hypothesis_verdict(r["estimate"], *r["ci95"], thr)
        out[h] = r
    p1 = A.protocol_contrast(run, claims["P1"][0], -1, 2000, 1000, retrievers=retr)
    out["P1_fixed512_drop_bm25"] = {"estimate": p1["estimate"], "ci95": p1["ci95"]}
    sw = {}
    for c in claims["S5"] + claims["S6"]:
        sw[c.cid] = {p: A.verdict_summary(A.claim_diffs(run, c, p, retrievers=retr), 2000) for p in ("count", "budget")}
        for p in sw[c.cid]:
            sw[c.cid][p].pop("by_dataset")
    out["semantic_wins_bm25"] = sw
    return out
res = {}
stored = A.Run(ROOT / "experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu", study="1b")
stored.validate("CONFIRMATORY", list(B.CHUNKINGS), {"chunkings": list(B.CHUNKINGS), "retrievers": list(B.RETRIEVERS)})
res["stored (word, float16)"] = quantities(stored, ["bm25"])
for v in ("word64", "char", "char_nows"):
    run = A.Run(sp / f"posthoc/e3_confirmatory_bm25/{v}", study="1b")
    run.validate("POSTHOC", list(B.CHUNKINGS), None)
    res[v] = quantities(run, ["bm25"])
(sp / "logs").mkdir(parents=True, exist_ok=True)
(sp / "logs/posthoc_summary_e3_bm25.json").write_text(json.dumps(res, indent=1))
for v, q in res.items():
    print(v, {k: (round(100 * x["estimate"], 1), [round(100 * c, 1) for c in x.get("ci95", [])], x.get("verdict_rule_at_threshold"))
              for k, x in q.items() if k != "semantic_wins_bm25"},
          "S5-128 count/budget sem:", round(100 * q["semantic_wins_bm25"]["S5-128"]["count"]["support_A"], 1),
          round(100 * q["semantic_wins_bm25"]["S5-128"]["budget"]["support_A"], 1))
