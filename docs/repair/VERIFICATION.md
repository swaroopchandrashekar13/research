# Verification matrices (2026-10-24; repeated on 2026-10-25 after the hash-removal pass)

Levels of evidence are kept separate. Tolerances were fixed before each comparison: integers, strings and verdict
labels exact; floats |Δ| ≤ 1e-12 (`tools/compare_results.py`); stored float16 scores compared exactly.

| Level | What was done | Result |
|---|---|---|
| Arithmetic check | shares, differences, Wilson interval, MDE formula, H3 formula recomputed from stored values | all match (`CLAIM_TRACE_MACROS.md`, below) |
| Same-code recomputation | `ragmv.analyze`, `analyze1b`, `analyze_generation` rerun on the stored runs into new directories (validation environment) | E1 975, E3 449, E2 639 fields identical; 0 differences beyond tolerance; 0 verdict changes. Only the redacted `git` fields and new metadata differ. Repeated 2026-10-25 on the runs with hash values removed (`HASH_REDACTIONS.md` §6): same counts, 0 differences |
| Independent statistical verification | `tools/independent_stats.py` (does not import `ragmv.stats`/`ragmv.analyze`) | 13/13 checks pass (table A); repeated 2026-10-25 with identical output |
| Retrieval re-execution | BM25 re-executed for all Study 1 universes and the Study 1b BM25 arm (`ragmv.posthoc`) | 85,275,648 + 1,665,540 stored values reproduced exactly; depths equal the manifests |
| Generation-input reconstruction | Tier 2 prompts, retrieval values and EM/F1 rebuilt from the verified data (`tools/validate_artifacts.py --data-root`) | 1,600/1,600 prompt SHA-256 equal (checked 2026-10-24; the stored prompt digests were removed on 2026-10-25, so this comparison can no longer be repeated from the repository); retrieval values equal E1 and the rebuilt jobs; EM/F1 0 mismatches; 2026-10-25: rebuilt prompts' context word counts, retrieval values, EM, F1 and answers again 0 mismatches |
| Dense retrieval re-execution | not done (bge-m3 embeddings of all corpora need a GPU) | **not verified** |
| Model-generation rerun | not done (no GPU; the generator is not deterministic across hardware) | **not verified** |
| Full experiment reproduction | not done (needs both of the above) | **not verified** |

## A. Independent statistical verification (stored results vs. independent implementation)
| Status | Check | Detail |
|---|---|---|
| PASS | Study 1 verdict shares (21 claims × 2 protocols × 4 datasets + pooled) | 480 quantities compared, 0 mismatches |
| PASS | Study 1 H1: estimate, joint-bootstrap CI and verdict rule | 71.1 pp [64.8, 81.9] → supported (identical) |
| PASS | Study 1 H1b | 26.7 pp [15.4, 33.9] → supported (identical) |
| PASS | Study 1 H2 η² (statsmodels OLS type II on universe means) | dataset 0.6143, retriever 0.0444, budget 0.0956, metric 0.0319 (identical) |
| PASS | Study 1 H3 required n (formula, ddof = 1) and rule | 85.4% > 500, median 1,256 (6,528 universes) |
| PASS | Study 1 sensitivity (a) BH as implemented | 68.0 pp |
| PASS | Study 1b shorter-arm orientation from manifest chunk statistics | 0 mismatches (also 24/24 identical when lengths are computed on confirmatory documents only) |
| PASS | Study 1b semantic-arm shares | 24 compared, 0 mismatches |
| PASS | Study 1b H4, H4b, H5, H5b point estimates and verdict rules | 55.4, 64.4, 19.4 (inconclusive), 58.3 pp (identical) |
| PASS | Tier 2 pooled DiD, stratified bootstrap CI and reading rule | 2 claims × 3 measures, 0 mismatches; 50 complete cases per dataset (0 dropped) |

## B. Post-hoc checks (not pre-registered; none changes a reported verdict)
| Check | Finding |
|---|---|
| Monte-Carlo seed (verdict bootstrap seeds 1–5 vs 7) | H1 70.5–71.0 pp vs 71.1 pp; 205 of 24,960 universe verdicts differ between seeds 7 and 1 |
| float16 storage | 673 universes have a CI bound within 2⁻¹¹ of zero; rescoring in float64 changes **0** universe verdicts and no estimate |
| Benjamini–Hochberg family | implemented per (claim, protocol, dataset): 68.0 pp; pooled over datasets: 70.4 pp |
| Universe weighting | equal weight per universe (192 per dataset for P1): 71.1 pp; datasets weighted by query count: 84.2 pp |
| H3 with document clustering | share > 500 85.2% (vs 85.4%), median 1,243; median design effect 1.02 |
| Tier 2 MDE for the equal-weight estimand | P1 F1 0.0676 vs reported 0.0683; all six measures agree to ≈ 0.001 |
| Character-based metrics (re-executed identical selections) | no hypothesis verdict changes; see `experiments/E1_retrieval_multiverse/analysis/posthoc-charmetric-20261024/README.md` |
| Study 1 net-share figure (FIG-001) | the published figure used 1,000 resamples; its points differ from the analysed shares by ≤ 0.009; no point crosses zero |

**Threshold-sensitive result: H5.** With the pre-registered verdict-bootstrap seed 7, H5 = 19.4 pp (threshold 20 pp,
CI [16.7, 41.7]) → inconclusive. With nine other seeds (1–6, 8–10; post-hoc) the H5 estimate is 21.5–24.3 pp, which
would meet the support rule (estimate ≥ 20 and lower bound > 0). The dense P1 grid has only 48 count-matched and 36
budget-matched universes, so a single universe verdict moves the share by 2.1–2.8 pp. The reported verdict follows the
pre-specified seed and is not changed; the manuscript now states that H5 is unresolved and Monte-Carlo sensitive. No
other hypothesis estimate or CI bound lies within these Monte-Carlo or float16 ranges of its threshold (H1 varies
70.5–71.1 pp across seeds; H5b 53.5–58.3 pp).

## C. Displays
| Display | Regenerated in isolation | Comparison with the baseline copy |
|---|---|---|
| `numbers.tex` | yes | the 145 original macros identical; 6 post-hoc macros added |
| 12 original tables | yes | 8 identical; 4 caption-only changes (BH family wording ×2, chunk-length wording, E2 caption: resample count from settings and the "does not establish absence" sentence); values identical |
| `posthoc_charmetric.tex` | yes | new |
| `speccurve_P1_coverage`, `speccurve_S3-256_coverage`, `study1b_dumbbell` | yes | rasterised pixel-identical to the baseline; PDF bytes differ only by metadata |
| `verdict_dumbbell` | yes | changed by design (FIG-001): plotted from the analysed shares |
| `refs.bib` | yes | the entry cited only by the deleted draft dropped; Simonsohn et al. author list corrected |
| Every plotted coordinate | `figures/*.coords.json` | dumbbells equal `results.json` shares exactly (test); specification-curve points equal per-universe CIs (test) |
