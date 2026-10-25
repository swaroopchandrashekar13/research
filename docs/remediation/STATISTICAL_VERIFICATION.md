# Statistical verification (2026-10-25)

Two independent routes check every reported statistic. The full record of the second is
`statistical_verification.json`; commands and exit codes of the latest run are in `VERIFICATION.md`.

## 1. Same-code recomputation

The stored analyses were recomputed from the stored per-query results with the current code, into new directories,
and compared field by field with the stored `results.json` (`tools/compare_results.py`). The files each recomputation
read were checked against `PROTECTED_SHA256.txt`.

| Analysis | Fields identical | Different | Missing | Consumed-input mismatches |
|---|---:|---:|---:|---:|
| E1 confirmatory (Study 1) | 975 | 0 | 0 | 0 |
| E3 confirmatory (Study 1b) | 449 | 0 | 0 | 0 |
| E2 analysed run (Tier 2) | 639 | 0 | 0 | 0 |
| E3 pilot (exploratory) | 449 | 0 | 0 | 0 |
| E1 pilot (exploratory) | 967 | **8** | 0 | 0 |
| E1 post-hoc character-metric analyses (3) | 1,002 each | 0 | 0 | — (new BM25 execution) |

**E1 pilot.** The 8 differing fields are bounds of the H1 sensitivity intervals (b)–(e) (largest difference 1.85
points, the lower bound of the document-cluster interval); every point estimate, every verdict and all other fields
are identical. The code as it stood before this review produces exactly the same values as the current code, so the
stored pilot analysis was computed by an earlier version of the analysis code, consistent with the post-run change to
the sensitivity intervals recorded in the Study 1 deviation log. The pilot is exploratory and supports no reported
claim; the stored file is kept unchanged.

**Tolerance.** Integers, strings, booleans and verdict labels must be identical; floats may differ by at most 1e-12,
the round-off of a JSON round trip (the recomputations use the same seeds and arithmetic, so any larger difference
is a defect). The comparison cannot be loosened beyond 1e-9 from the command line, and it fails on a missing, a
non-finite or a type-changed scientific value. Only the metadata fields it names (code and input identities,
validation notes, source-manifest echoes) may differ. Apart from the E1 pilot, no field differs.

## 2. Independent recomputation

`tools/independent_stats.py` does not import `ragmv.stats` or `ragmv.analyze`: from the analysis plans it
re-implements the per-universe paired percentile bootstrap (2,000 resamples, seed 7), the joint bootstrap of shares
(1,000 replicates, seed 11; seed 13 for H2) with normal-approximation verdicts inside replicates, the verdict and
support rules, Benjamini–Hochberg, η² (statsmodels type II), the H3 power formula and the Tier 2 stratified
bootstrap, and reads only the stored arrays, manifests and logs.

| Check | Result |
|---|---|
| Study 1 verdict shares (21 claims × 2 protocols × 4 datasets + pooled) | PASS: 480 quantities, 0 mismatches |
| H1 estimate, joint-bootstrap CI and verdict | PASS: 71.1 pp [64.8, 81.9], supported |
| H1b | PASS: 26.7 pp [15.4, 33.9], supported |
| H2 η² and bootstrap fraction | PASS: dataset 0.6143, retriever 0.0444, budget 0.0956, metric 0.0319; largest in 100.0 % |
| H3 required n | PASS: 85.4 % above 500, median 1,256 (6,528 universes) |
| H1 sensitivity (a) BH as implemented; (b)–(e) with CIs | PASS: 68.0; 61.5 [53.2, 74.8]; 70.8 [64.6, 85.4]; 69.7 [63.8, 82.0]; 74.2 [68.3, 84.8] |
| Study 1b shorter-arm orientation from manifest chunk statistics | PASS: 0 mismatches |
| Study 1b semantic-arm shares (6 claims × 2 protocols) | PASS: 24 quantities, 0 mismatches |
| H4 | PASS: 55.4 pp [50.8, 63.1], supported |
| H4b | PASS: 64.4 pp [56.5, 68.3], supported |
| H5 (equal to the recorded values) | PASS: 19.4 pp [16.7, 41.7], inconclusive |
| H5b | PASS: 58.3 pp [45.1, 64.6], supported |
| Study 1b CUAD dense P1 subset (10 fields) | PASS: 0 mismatches |
| H4 sensitivity (a), (b), (d), (e), (f) | PASS: 54.3; 48.0 [42.7, 58.3]; 58.7 [50.0, 63.3]; 53.7 [49.7, 60.9]; BM25 61.1 [57.2, 72.5], dense 49.8 [39.1, 58.1] |
| Tier 2 pooled DiD, CI and reading rule (2 claims × 3 measures) | PASS: 0 mismatches; 50 complete queries per dataset |
| Tier 2 per-dataset contrasts, cell means, complete-case counts | PASS: 236 quantities, 0 mismatches |

22 of 22 checks pass.

## 3. Post-hoc quantities (not part of the analysis plans)

| Quantity | Value | Where it is used |
|---|---|---|
| BH family pooled over datasets (H1 sensitivity a) | 70.4 pp (per dataset, as implemented: 68.0 pp) | manuscript, deviations |
| Normal-approximation full-sample estimates (the statistic the joint replicates use) | H1 70.9, H1b 27.1, H4 55.6, H4b 65.3, H5 21.5, H5b 58.3 pp; the largest gap to the planned estimate apart from H5 is 0.9 pp | manuscript, analysis plan section |
| H5 with nine other verdict-bootstrap seeds | 21.5–24.3 pp (seed 7: 19.4 pp); 48 and 36 universes | manuscript, Study 1b results |
| Monte-Carlo robustness of H1 (seeds 1–5) | 70.5–71.0 pp (seed 7: 71.1); 205 of 24,960 universe verdicts change between seeds 7 and 1 | record only |
| Universes with a CI bound within 2⁻¹¹ of zero (float16 storage) | 673 of 24,960; re-executed with float64 storage, 0 of 24,960 Study 1 universe verdicts change | manuscript, post-hoc appendix |
| H1 with datasets weighted by query count instead of equal universe weight | 84.2 pp (planned equal weight: 71.1 pp) | record only |
| H3 with documents as clusters (design effect) | 85.2 % above 500, median 1,243; median design effect 1.02 | record only |
| Tier 2 MDE of the equal-weight estimand | P1 F1 0.068 (pooled-SD MDE 0.068) | manuscript |
| Budget-underfill upper bound | no verdict changes; H4 at most 55.9 pp (+0.5) | manuscript (`underfill_bound.json`) |

## 4. Not covered

- The independent checker uses the same seeds and NumPy generator as the analysis, so it reproduces the same
  bootstrap draws: it tests the implementation, not Monte-Carlo variability (the seed analyses above address that).
- Retrieval itself (BM25 scoring, chunking) is checked by re-execution against the data (tests and the post-hoc
  analyses), not by the statistical checker. Dense retrieval scores and Tier 2 generations are not re-executed (GPU).
- Tier 2 EM/F1 are re-scored from the stored responses with the package's own scorer, not an independent one.
