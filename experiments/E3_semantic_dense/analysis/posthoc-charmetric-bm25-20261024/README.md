# POST-HOC SENSITIVITY (2026-10-24): character-based metrics, Study 1b BM25 arm only — not part of the analysis plans

Same motivation and method as `experiments/E1_retrieval_multiverse/analysis/posthoc-charmetric-20261024/README.md`.
BM25 retrieval over the stored fixed and semantic chunk boundaries (`chunks_*.json.gz`) was re-executed
(`python -I -m ragmv.posthoc study1b`); the re-executed word scores and word counts equal the stored BM25 arrays for
all **1,665,540** values (`selection_equivalence.json`: 0 mismatches).

| Quantity (BM25 universes only; pp) | stored (word, float16) | word64 | char | char_nows |
|---|---|---|---|---|
| H4 form, S5 (shorter arm, budget − count) | 61.1 [57.2, 72.5] | 61.1 [57.2, 72.5] | 60.2 [54.9, 70.4] | 62.0 [57.2, 72.5] |
| H4b form, S6 | 63.9 [55.3, 71.1] | 63.9 [55.3, 71.1] | 60.2 [52.8, 67.8] | 63.9 [55.3, 71.1] |
| P1, shorter arm (fixed-128) | 91.7 [80.6, 91.7] | 91.7 [80.6, 91.7] | 88.9 [80.6, 91.7] | 91.7 [80.6, 91.7] |
| P1, fixed-512 share drop (count − budget) | 70.8 [64.6, 85.4] | 70.8 [64.6, 85.4] | 70.8 [64.6, 83.3] | 70.8 [64.6, 85.4] |

The stored-word BM25 value of the H4 form equals the stored planned sensitivity (f) "BM25 only"
(61.1 [57.2, 72.5]). Every quantity stays above its threshold under every variant.

**Not quantified:** the dense-retrieval (bge-m3) arm, and therefore H4 and H4b as pooled over both retrievers, H5 and
H5b. Re-executing dense retrieval needs the bge-m3 embeddings of all corpora (GPU); it was not done, so the
character-metric impact on those results is unquantified.
