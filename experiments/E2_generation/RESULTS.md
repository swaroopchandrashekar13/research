# E2 Tier 2 results — answer quality (EXPLORATORY)

*2026-10-19 · plan `ANALYSIS_PLAN.md` (written before any job) · run `runs/qwen3-4b-kaggle-gpu` (Kaggle, Tesla T4,
llama-cpp-python 0.3.36 CUDA, clean tree) · analysis `analysis/qwen3-4b-kaggle-gpu` · this is the analysed run under
the "first complete run" rule in `research/preregistration.md` §8.*

> **Provenance note (2026-10-24).** The commit identifier originally cited for this run is unresolvable (the original
> version history is no longer available) and was removed; see `docs/repair/HASH_REDACTIONS.md`. The decision log
> this summary originally referred to is not in the repository.

**Not part of the frozen confirmatory hypotheses (H1–H3); it cannot change their verdicts.**

## Integrity checks (done before reading the results)
- 1,600/1,600 jobs, 400 per dataset, all `status: ok`, one row per job, every row from
  `Qwen/Qwen3-4B-GGUF@bc640142c66e/Qwen3-4B-Q4_K_M.gguf` on `Tesla T4 | n_gpu_layers -1`.
- Every prompt's SHA-256 equals the prompt rebuilt locally from the pre-registered sample (0 mismatches); every row's
  retrieval metrics equal E1's measurements for that query (0 mismatches); EM/F1 recomputed from the stored responses
  (0 mismatches); the analysis rerun locally reproduces `results.json` exactly.
- The researcher uploaded the files (zip SHA-256 in `runs/qwen3-4b-kaggle-gpu/UPLOAD_SHA256`); the GPU build log is kept
  as `build_gpu.log.gz`.
- *[Note added 2026-10-25: at the researcher's request, the prompt digests, model revisions and model-file digests in the
  run files, the upload-archive digest and the hex identifiers in the build log were removed
  (`docs/repair/HASH_REDACTIONS.md` §6). The prompt-digest comparison above was repeated on 2026-10-24, before removal,
  with 0 mismatches; it can no longer be repeated from the repository.]*

## Pre-specified result (pooled over 4 datasets, 200 queries; stratified bootstrap, 2,000 resamples)
DiD = Δ(budget 1,024 words) − Δ(top-5), Δ = metric(A) − metric(B). E1's mechanism predicts DiD > 0.

| Claim | Measure | DiD | 95% CI | Minimum detectable | Reading |
|---|---|---:|---|---:|---|
| P1 (fixed-128 vs fixed-512) | **answer F1** | −0.017 | [−0.065, +0.033] | 0.068 | inconclusive |
| | exact match | −0.055 | [−0.100, −0.010] | 0.066 | opposite |
| | retrieval coverage (same queries) | +0.089 | [+0.050, +0.132] | 0.059 | carries over |
| S3-256 (paragraph vs fixed) | **answer F1** | +0.004 | [−0.024, +0.036] | 0.044 | inconclusive |
| | exact match | −0.015 | [−0.050, +0.020] | 0.051 | inconclusive |
| | retrieval coverage (same queries) | +0.035 | [+0.015, +0.060] | 0.036 | carries over |

## What this says
1. **The sample reproduces E1's retrieval reversal** (coverage DiD > 0 for both claims), so the queries are not atypical.
2. **For this reader, a carry-over of the retrieval reversal to answer F1 was not detected.** Answer-F1 DiDs are near
   zero and their 95% intervals include zero (upper bounds about +0.03 for P1 and +0.04 for S3-256). This is an
   inconclusive result, not evidence of no effect: the minimum detectable DiDs (0.068 and 0.044) are of the same order
   as the intervals. For P1, exact match moves in the *opposite* direction: once text is equalised, the 512-word arm
   answers exactly more often (interval excludes zero).
3. Consequence for the paper: the protocol dependence is established for **retrieval evaluation** (E1). Whether it
   changes downstream conclusions depends on the reader and was not resolved for this 4B instruction model. The paper
   must not claim that count-matched studies reach wrong *answer-quality* conclusions, nor that they reach right ones.

*(Wording qualified 2026-10-24: the earlier text said the reversal "does not carry over" and that the intervals
"exclude effects larger than" their upper bounds, which read an inconclusive interaction as an absence of effect.
The numbers are unchanged.)*

## Diagnostics (pre-specified) and one exploratory observation
| Dataset | Truncated answers (256-token cap) | "Unanswerable" replies |
|---|---|---|
| SQuAD 2.0 | 0 | 4.3% |
| COVID-QA | 0 | 5.8% |
| CUAD | 65 / 400 | 15.0% |
| Qasper | 2 / 400 | 15.8% |

- Truncation is almost all in CUAD (long contract-clause answers; mean gold length 52 words), spread over all arms;
  truncated answers still score F1 0.23 and CUAD's P1 DiD is −0.001, so truncation does not drive the pooled result.
- "Unanswerable" is spread evenly, except the arm with least text (Qasper, fixed-128, top-5: 13/50), as expected.
- **Exploratory (not pre-registered):** at an equal 1,024-word budget, SQuAD answer F1 is 0.58 with two 512-word
  chunks vs 0.44 with eight 128-word chunks, at nearly the same retrieval coverage (0.88 vs 0.86 on these 50
  queries). A contiguity benefit for the reader (fewer, longer passages) would explain why retrieval gains do not
  become answer gains. Hypothesis for follow-up, not a finding.
  *Correction 2026-10-20: an earlier version said the 128-word arm "covers more gold text"; the logged means
  (`analysis/qwen3-4b-kaggle-gpu/results.json`, `datasets.squad2.means`) show slightly lower coverage (0.86 vs 0.88).
  Found while generating the manuscript macros from the results file.*

## Limits
One reader (Qwen3-4B, Q4_K_M, greedy), one sample, 50 queries per dataset; SQuAD-style F1 penalises verbose correct
answers (CUAD, Qasper golds are long). A stronger reader or more queries could detect smaller effects.
