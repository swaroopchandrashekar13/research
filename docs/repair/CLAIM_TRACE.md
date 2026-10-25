# Manuscript claim-verification matrix (canonical `manuscript/main.tex`, 2026-10-24)

**Numbers.** Every result value in the text and the hypothesis table is a macro; all 115 macros used were recomputed
independently from their source files and match (`CLAIM_TRACE_MACROS.md`, `tools/trace_claims.py`, exit 0). The
generated tables are regenerated from the same files (`manuscript/build_displays.py`; `VERIFICATION.md` §C). Not every
number is generated: the literal numbers in the prose are design constants (dataset names; 16 chunkings and 16
retrievers; k ∈ {1,3,5,10}; B ∈ {128,…,2048}; the grid products 4×16×4×3 and 4×16×3×3; seeds 20261018, 20261019, 7,
11, 13; 2,000 / 1,000 resamples; thresholds 20/10 pp, 95%, 500 queries, |δ| = 0.02, 1.96 + 0.8416; 50 queries per
dataset; 256-token cap; 8,192-token encoder limit; λ = 0.5; 95th percentile; 512-word cap; 0.009 figure shift and
≈0.001 MDE agreement in Appendix A, both from `VERIFICATION.md`). Each was checked against the code
(`src/ragmv/run.py`, `stats.py`, `semantic.py`, `generate.py`, `analyze*.py`) or the verification files.

**Assertions.** Verification levels: *R* = checked against the result files; *C* = checked against code; *V* =
checked by an independent recomputation; *L* = literature claim (identity checked, content not read in full).

| Location | Assertion | Evidence | Level | Status |
|---|---|---|---|---|
| Abstract; Study 1 results | Budget matching reduces support for 512- over 128-word chunks by 71.1 pp [64.8, 81.9] | E1 `results.json` H1; independent joint bootstrap | R, V | supported |
| Abstract; Study 1b results | Shorter-arm support rises by 55.4 pp [50.8, 63.1] for breakpoint chunking | E3 H4; independent point estimate | R, V | supported |
| Abstract; Study 1b results | Original dense-retrieval hypothesis is inconclusive | E3 H5 = 19.4 pp (rule: < 20) | R, V | supported; **Monte-Carlo sensitive** (21.5–24.3 pp with nine other seeds; now stated in the Study 1b results) |
| Abstract; answer-quality results | Coverage contrasts positive; answer-F1 interactions inconclusive and not evidence of absence; EM opposite | E2 pooled DiD: coverage CIs > 0; F1 CIs include 0; P1 EM CI [−0.100, −0.010] | R, V | supported (wording qualified, CLAIM-002) |
| Problem formulation | Metrics are computed on words after mapping gold character spans to the words they overlap | `data.char_to_word_span`, `evaluate.span_metrics`; tests `test_metric_definitions.py` | C | supported (correction of the earlier "characters", MAN-001) |
| Problem formulation; App. D | A character-based rescoring of identical selections changes no hypothesis verdict | post-hoc runs; 85.3 M + 1.7 M stored values reproduced; analysis with unchanged code | R, V | supported for BM25; dense arm unquantified (stated) |
| Study 1, analysis plan | Bootstrap and joint-bootstrap schemes, seeds, H2 seed, document-cluster scheme | `analyze.py` (`SEEDS`), `stats.py` | C | supported (description corrected, STAT-001) |
| Study 1, analysis plan | BH applied per claim, protocol and dataset; pooled family gives 70.4 pp | `analyze.verdict_summary`; independent BH | C, V | supported (correction, STAT-001) |
| Study 1, analysis plan | Universes have equal weight; datasets equally represented | 192 universes per dataset for P1 | R | supported |
| Study 1 results | Mean P1 difference changes sign between protocols in each dataset | `by_dataset.mean_delta`: all four negative under count, positive under budget | R | supported |
| Study 1 results | CUAD has few decisive count-matched settings; Qasper mixed under budget | CUAD count support for 512: 26%; Qasper budget 44% / 31% | R | supported |
| Study 1 results | Overlap (S2) comparisons change much less | S2-128 51.6% → 55.1%; S2-256 36.1% → 39.8% | R | supported |
| Study 1 results | S1-64: the 128-word arm keeps support under budget matching | S1-64 budget: 20.0% (64) vs 42.1% (128) | R | supported |
| Study 1 results | Dataset has the largest η² for S3-256 in 100% of replicates | H2; η² recomputed with statsmodels | R, V | supported |
| Study 1b | Breakpoint arm longer than fixed-128/256 and shorter than fixed-512 | mean lengths 278–320 vs 247–252 and 477–495 words | R | supported |
| Study 1b | Against fixed-512 the breakpoint arm's support increases under budget matching | S5-512 semantic share 7.3% → 68.1% | R | supported |
| Study 1b | Shorter arm determined from corpus-average lengths before metrics | manifests' `chunk_stats`; same result on confirmatory documents only (24/24) | R, V | supported |
| Answer-quality check | All scheduled generations completed | 1,600/1,600 ok rows; 0 duplicates | R | supported |
| Answer-quality check | Prompts and retrieval are those E1 measured | 1,600/1,600 prompt digests rebuilt (2026-10-24, before the stored digests were removed); retrieval values equal E1 | V | supported |
| Protocol audit | Audit: 19 studies; 4 candidates from logged searches, 15 from unlogged sessions; single AI coder; no κ | `candidates.csv` `source`; `coding.csv` `coder` | R | supported (corrected, AUDIT-001/DOC-002) |
| Discussion | Text allowance is consistent with, not identified as, the cause | design | — | appropriately hedged |
| Limitations | Plans' timing cannot be verified | original history unavailable | — | supported (replaces earlier chronology claims) |
| Related work | Characterisations of cited studies | `literature/bibliography.yaml` (L1/L2), protocol-audit coding | L | **not fully verified**: no cited work is at L3 (read in full) |
| Reproducibility | Repository URL, generated macros/tables/figures, claim trace | this file; `build_displays.py` | R | supported |
