# Errata and annotations for the surviving analysis plans

*Written 2026-10-24 during the repository repair. The plans themselves are **not** edited for these points (their
only edits are the two Git-reference redactions listed in `docs/repair/HASH_REDACTIONS.md`); this file records
corrections to their cross-references and the discrepancies found between the plans and the implementation. No
hypothesis, threshold, estimand or analysis choice is changed by this erratum, and no logged deviation is removed.*

SHA-256 of the files this erratum annotates (as of this erratum): see `docs/repair/PROTECTED_SHA256.txt`.

## A. Section-number errors (cross-references point to the wrong section)

| File | Text as written | Should read | Note |
|---|---|---|---|
| `research/preregistration.md` §8, row "Post-pilot clarification" | "§5.3 wording changed" | §4, item 3 | the analysis plan is §4 |
| `research/preregistration_study1b.md` header ("Version" field) and §4 (H5b row) | "post-pilot amendment, §9" | §8 | the deviations log is §8 |
| `research/preregistration_study1b.md` §2 | "Identical to Study 1 (§2 of v1.0)" | Study 1 §1 | Study 1 data and splits are in §1 |
| `research/preregistration_study1b.md` §4 | "exactly as Study 1 §4" | Study 1 §3 | verdicts and the joint bootstrap are specified in Study 1 §3 |
| `research/preregistration_study1b.md` §5 | "Study 1 §5 applies unchanged" | Study 1 §4 | the analysis plan and sensitivity analyses (a)–(e) are Study 1 §4 |
| `experiments/E2_generation/ANALYSIS_PLAN.md` header | "pre-registration v1.0 §4"; "§6 as amended in §9" | §3; §5 as amended in §8 | |
| `experiments/E1_retrieval_multiverse/RESULTS.md` (summary, corrected in place) | "`research/preregistration.md` §9" | §8 | |
| code docstrings in `src/ragmv/` (corrected in place) | "preregistration §3.1 / §3.2 / §4 / §3.3-§5" | §2.1 / §2.2 / §3 / §2.3–§4 | |

## B. Discrepancies between the plans and the implementation (disclosed, not silently resolved)

1. **Metric unit (all studies).** Study 1 §2.2 defines hit_strict, hit_lenient and coverage over *characters*
   ("≥ 50% of its characters retrieved", "fraction of its characters retrieved"). The implementation converts each gold
   character span to the half-open interval of `\S+` words it overlaps and scores **word** overlap
   (`ragmv.data.char_to_word_span`, `ragmv.evaluate.span_metrics`). All stored and reported results are word-based.
   Study 1b and Tier 2 inherit the same metrics. The two definitions are not equivalent: retrieving only "a" from the
   gold span "a bbbbbbbbb" gives word coverage 1/2 but character coverage 1/11 (regression tests in
   `tests/test_metric_definitions.py`). A post-hoc character-based rescoring of identical, re-executed BM25 selections
   changes no hypothesis verdict
   (`experiments/E1_retrieval_multiverse/analysis/posthoc-charmetric-20261024/`,
   `experiments/E3_semantic_dense/analysis/posthoc-charmetric-bm25-20261024/`); the dense-retrieval arm is unquantified.
2. **Benjamini–Hochberg family (Study 1 §4 (a); Study 1b §5).** The plan says "within claim". The implementation
   applies BH separately to each (claim, protocol, dataset) set of universes. Post-hoc, pooling over datasets gives
   70.4 pp instead of 68.0 pp for H1 sensitivity (a) (`docs/repair/statistical_verification.json`).
3. **"Shorter arm" corpus (Study 1b).** §4 says the shorter arm is determined "from chunk statistics on the
   confirmatory corpus"; §3.5 item 5 says "over the full retrieval corpus". The implementation follows §3.5 (full
   corpus, from the run manifests). Checked 2026-10-24 with the verified datasets: mean chunk lengths over the confirmatory
   documents alone give the same shorter arm as the full corpus in all 24 (dataset, claim) cases, so this
   inconsistency does not affect any result.
4. **Provenance fields (Study 1 §6).** The plan says every run manifest records a "git SHA". The original commits are
   unresolvable and were redacted; runs created after 2026-10-24 record a content digest of the code instead.
5. **Header of the Study 1 plan.** The surviving `research/preregistration.md` begins at "## 1. Data"; it carries no
   title or version block, so its version label cannot be confirmed from the file itself. Other documents refer to it
   as version 1.0.
6. **Chronology.** The plans and logs state when versions were frozen and when deviations were made. The original
   version-control history is unavailable, so none of these statements can be independently verified; the repaired
   manuscript does not assert them.

## C. Statements in the Study 1b plan's motivation
§0 ("Motivation", item 3) says Tier 2 "found the retrieval reversal did **not** carry over to answer F1". The Tier 2
answer-F1 interactions are inconclusive (95% intervals include 0); they do not establish the absence of an effect.
