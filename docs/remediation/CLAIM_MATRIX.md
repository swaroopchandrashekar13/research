# Manuscript claim matrix (2026-10-26)

Entry point: `manuscript/main.tex`, which inputs `numbers.tex` (generated result macros), `tables/*.tex` (generated
tables), `figures/*.pdf` (generated figures) and `refs.bib` (generated from `literature/bibliography.yaml`). Two
variants are built from the same source: the named one and an anonymous one (`-jobname=main-anonymous`, with
`\AnonymousSubmission`).

How the numbers are verified:

- **Trace** (`tools/trace_claims.py`, output in `CLAIM_TRACE_MACROS.md`): every result macro of `numbers.tex` is
  recomputed from the field of the result file it comes from, without the generator; a macro that cannot be traced or
  differs fails.
- **Regeneration** (`manuscript/build_displays.py --compare manuscript`): numbers, tables, figures (coordinate
  sidecars and PDF bytes) and the bibliography are regenerated into a new directory and compared with the committed
  copies.
- **Same-code recomputation**: each stored `results.json` is recomputed from the stored per-query results and
  compared field by field (`tools/compare_results.py`).
- **Independent recomputation** (`tools/independent_stats.py`, `STATISTICAL_VERIFICATION.md`): estimates, intervals
  and verdicts recomputed by code that does not import the analysis package.

Status: **PASS** verified as stated; **PARTIAL** verified with a stated limitation; **UNVERIFIED** cannot be checked
from the materials. Results of the latest runs: `VERIFICATION.md`.

## 1. Results

| ID | Location | Text or macro (value) | Source and field | Independent check | Status |
|---|---|---|---|---|---|
| R1 | Abstract; Study 1 data | `\EoneNq` (9,253 confirmatory queries; 4,744 / 1,771 / 996 / 1,742) | E1 run `queries.json` lengths; `tables/data.tex` | query lists rebuilt from the data and the deterministic split (`validate_artifacts --data-root`) | PASS |
| R2 | Abstract; Study 1 results; hypotheses table; Conclusion | H1 `\HOneEst` 71.1 pp [64.8, 81.9], supported | E1 `results.json` `H1` | H1 joint bootstrap and verdict rule | PASS |
| R3 | Study 1 results | P1 shares count 78.8 % / 0.0 %, budget 7.6 % / 81.2 % | E1 `verdict_shares.P1` | Study 1 verdict shares (480 quantities) | PASS |
| R4 | Study 1 results | H1 sensitivities 68.0, 61.5, 70.8, 69.7, 74.2 pp | E1 `H1_sensitivity` | sensitivity (a) and (b)–(e) with CIs | PASS |
| R5 | Study 1 analysis plan | BH pooled over datasets 70.4 pp (post-hoc) | `statistical_verification.json` `posthoc.BH_family_P1` | computed by the independent checker itself | PASS (post-hoc) |
| R6 | Study 1 results | S2-128 / S2-256 overlap shares; S1-64 shares | E1 `verdict_shares` | Study 1 verdict shares | PASS |
| R7 | Study 1 results; hypotheses table | H1b 26.7 pp [15.4, 33.9], supported | E1 `H1b` | H1b joint bootstrap | PASS |
| R8 | Study 1 results; hypotheses table | H2 η² dataset 0.61, retriever 0.04, largest in 100.0 %, supported | E1 `H2` | statsmodels type II η²; bootstrap fraction (seed 13) | PASS |
| R9 | Study 1 results; hypotheses table | H3 85.4 % above 500, median 1,256, supported | E1 `H3` | H3 required n | PASS |
| R10 | Study 1 analysis plan | normal-approximation gap at most 0.9 pp except H5 | `posthoc.normal_verdict_point_estimates` | independent checker | PASS (post-hoc) |
| R11 | Abstract; Study 1b results; hypotheses table; Conclusion | H4 55.4 pp [50.8, 63.1], supported; 9.4 % → 64.8 % | E3 `H4` | H4 joint bootstrap; shorter-arm orientation | PASS |
| R12 | Study 1b results | H4 BM25-only 61.1 pp, dense-only 49.8 pp | E3 `H4_sensitivity` | H4 sensitivities (a), (b), (d), (e), (f) | PASS |
| R13 | Study 1b results | S5-128 semantic-arm shares 60.4 % (count) / 8.3 % (budget) | E3 `semantic_wins` | semantic-arm shares (24) | PASS |
| R14 | Study 1b results; hypotheses table | H4b 64.4 pp [56.5, 68.3], supported | E3 `H4b` | H4b joint bootstrap | PASS |
| R15 | Study 1b results; hypotheses table | H5 19.4 pp [16.7, 41.7], inconclusive; 25.0 % → 5.6 % | E3 `H5` | H5 joint bootstrap, equal to the recorded values | PASS |
| R16 | Study 1b results | H5 with 9 other seeds 21.5–24.3 pp; normal-verdict estimate 21.5 pp (post-hoc) | `posthoc.H5_seed_sensitivity`, `posthoc.normal_verdict_point_estimates` | independent checker | PASS (post-hoc) |
| R17 | Study 1b results; hypotheses table | H5b 58.3 pp [45.1, 64.6], supported; amendment | E3 `H5b`; plan's deviation log | H5b joint bootstrap | PASS |
| R18 | Study 1b design; chunk-length table | semantic chunk means 278–320 and 452–458 words; ≥ 92.0 % non-contiguous | E3 manifests `chunk_stats` | chunk files partition every document exactly (`validate_artifacts --data-root`) | PASS |
| R19 | Study 1 design; Study 1b design | universe counts 768 / 576; 96 / 72; 48 / 36 | `n_universes` in E1 `verdict_shares.P1`, E3 `semantic_wins`, E3 `H5` | traced; the text's products 4×16×4×3 = 768 and 4×16×3×3 = 576 hold | PASS |
| R20 | Answer check results | Tier 2 coverage DiD +0.089 [+0.050, +0.132] and +0.035 [+0.015, +0.060] | E2 `pooled` | Tier 2 pooled DiD | PASS |
| R21 | Answer check results; Abstract | answer-F1 DiD −0.017 [−0.065, +0.033] and +0.004 [−0.024, +0.036], inconclusive | E2 `pooled` | Tier 2 pooled DiD | PASS |
| R22 | Answer check results; Abstract | P1 exact-match DiD −0.055 [−0.100, −0.010], opposite | E2 `pooled` | Tier 2 pooled DiD | PASS |
| R23 | Answer check results | cell means 0.105 / 0.090 / 0.085 / 0.125; SQuAD F1 0.58 / 0.44 at coverage 0.88 / 0.86 | E2 `datasets.*.means`, `pooled` | Tier 2 per-dataset contrasts and cell means (236) | PASS |
| R24 | Answer check results | MDE 0.068 (pooled SD) and 0.068 (equal-weight, post-hoc) | E2 `pooled.*.mde`, `mde_stratified` | `posthoc.tier2_mde` | PASS |
| R25 | Answer check results; diagnostics appendix | 65 / 400 CUAD and 2 / 400 Qasper outputs at the cap; all 1,600 generations completed | E2 `diagnostics.finish_reasons`; generation logs | log scan (1,600 rows, all `ok`) | PASS |
| R26 | Audit | audit 19 papers; 12 fixed-count, 1 budget-matched, 3 with uncertainty; 9 exposed, 47.4 % [27.3, 68.3] | `literature/protocol_audit/coding.csv` | counts and Wilson interval recomputed from the coding by the trace | PARTIAL: no independent coding or reliability statistic |
| R27 | Limitations; deviations appendix | 2 underfilled selections (1,880 and 1,789 words); bound: no verdict changes, H4 at most 55.9 pp (+0.5) | `budget_underfill_census.json`, `underfill_bound.json` | census over all 168 stored arrays; bound computed with the plan written first (`POSTHOC_PLAN_underfill_bound.md`) | PASS (post-hoc bound) |
| R28 | Post-hoc appendix | character-metric sensitivity: 965 of 24,960 Study 1 universe verdicts change, no hypothesis verdict changes; 85,275,648 and 1,665,540 stored elements reproduced | posthoc analyses and `selection_equivalence.json` | BM25 re-executed from the data; dense arm not covered | PARTIAL: BM25 only |
| R29 | all tables and figures | every table cell and plotted coordinate | the result files above | regenerated and compared (0 differences) | PASS |

## 2. Methods, deviations and statements about the materials

| ID | Location | Statement | Evidence | Status |
|---|---|---|---|---|
| M1 | Study 1 data | splits ≈ 20/80 by document, seed 20261018; the full collection stays indexed | `ragmv.data.split_documents`; query lists rebuilt from the data | PASS |
| M2 | Study 1 design | 16 chunkers, 16 BM25 configurations, `bm25s` 0.2.13, k ∈ {1,3,5,10}, B ∈ {128,…,2048}, admissible B ≥ max(W_A, W_B) | `ragmv.chunking`, `ragmv.retrieval`, run manifests, `requirements/core.txt` | PASS |
| M3 | Study 1 analysis plan | 2,000 resamples (seed 7); 1,000 joint replicates (seed 11); H2 seed 13 | `ragmv.analyze.SEEDS`; stored `analysis_settings` | PASS |
| M4 | Study 1 analysis plan; deviations appendix | BH family is claim × protocol × dataset, not "within claim" as the plan says | code and erratum | PASS |
| M5 | Study 1 analysis plan | the document-cluster analysis resamples documents in both stages; inner normal verdicts use the query-level SD | `ragmv.stats`, independent checker | PASS |
| M6 | Study 1b design | breakpoint at the 95th percentile; clustering λ = 0.5, threshold 0.5, 512-word cap; an adaptation of Qu et al. | `ragmv.semantic`; Qu et al. read in full | PASS |
| M7 | Study 1b design | shorter arm from corpus-average chunk lengths computed before retrieval metrics | manifests' `chunk_stats`; orientation check | PASS (the order of computation is checked in the code, not in the historical run) |
| M8 | Answer check setup | 50 queries per dataset, seed 20261019; top-5 and 1,024-word budget; greedy, thinking off, 256 tokens | `jobs_meta.json`; sample rebuilt from the data | PASS |
| M9 | implementation appendix | code pins bge-m3 revision `5617a9f61b02` and the Qwen3-4B GGUF file revision `bc640142` with its SHA-256; the runs' own records of these are not part of the materials | `src/ragmv/dense.py`, `src/ragmv/generate.py`; `HASH_POLICY.md` | PASS (the stored runs' model identity is UNVERIFIED) |
| M10 | Study 1 analysis plan; Study 1b design; Limitations | the timing of the plans cannot be verified; no claim about it is made | original version history unavailable | PASS |
| M11 | deviations appendix | deviations as logged (timing as the logs record it) | plans' deviation logs; `research/ERRATA_preregistrations.md` | PARTIAL: timing UNVERIFIED |
| M12 | Audit | audit provisional: no blind independent coding, no reliability coefficient; candidate frame partly unlogged (4 of 19 from logged searches) | `coding.csv` (its `coder` column records who coded), `literature/search_log.md` | PASS |
| M13 | Reproducibility | every stored statistic recomputed with no difference; principal results recomputed independently | compare (E1 975, E3 449, E2 639 fields identical); independent checks | PASS |
| M14 | Reproducibility | identities removed from the stored runs cannot be checked; dense retrieval and generation not re-executed | `HASH_POLICY.md`; GPU not available | PASS |
| M15 | Limitations | metrics on words, not characters as the plans state; dense arm unquantified | erratum B1; post-hoc analysis | PASS |
| M16 | Related work; Audit | literature claims | `CITATION_SUPPORT.md` | PARTIAL: 4 uses at L3; 5 at L1 (identities of all 39 works confirmed) |
