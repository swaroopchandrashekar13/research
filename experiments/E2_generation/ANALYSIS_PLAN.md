# E2 Tier 2 generation — analysis plan (EXPLORATORY)

*Written 2026-10-19, committed before any Tier 2 job was run. Tier 2 is exploratory: it is not part of the frozen
confirmatory hypotheses (pre-registration v1.0 §4) and cannot change their verdicts. Design: pre-registration §6 as
amended in §9 (2026-10-19, two rows).*

## Question
RQ5: does the retrieval-level protocol reversal found in E1 carry over to the quality of generated answers?

## Design (fixed)
| Item | Value |
|---|---|
| Queries | 50 per dataset, seeded (20261019) sample of the confirmatory split; 4 datasets, 200 queries |
| Claims | P1 (A = fixed-128, B = fixed-512) and S3-256 (A = paragraph-256, B = fixed-256) |
| Operating points | count-matched top-5; budget-matched 1,024 words |
| Retriever | Lucene BM25, k1 = 1.5, b = 0.75, stemmed (the E1 default; text equals E1's retrieval, checked by test) |
| Generator | **Qwen3-4B** (Q4_K_M GGUF, HF commit `bc640142`, SHA-256 checked), llama.cpp on CPU, greedy (temperature 0, top-k 1), thinking off, max 256 output tokens, one sample. *Amended 2026-10-19 before the run (pre-registration §9): originally `gemini-3.6-flash`; stopped by the free tier's 20 requests/day after 21 jobs (kept, not analysed).* |
| Model identity | recorded per row (`model_version` = repo@commit/file; `hardware` = GPU/CPU, llama-cpp build, offload) and in `jobs_meta.json`. Analysed run: the first of `runs/qwen3-4b-kaggle-gpu` / `runs/qwen3-4b-kaggle-cpu` to reach 1,600 jobs (decision 029); CPU and GPU rows never pooled; any other complete run only as a hardware-robustness check |
| Metric | SQuAD-style token F1 (primary) and exact match, max over gold answers |
| Jobs | 200 queries × 4 chunkings × 2 operating points = 1,600 |

## Estimands
For claim (A, B), operating point o and query q: d_q(o) = F1_q(A, o) − F1_q(B, o).
Reversal statistic: **DiD_q = d_q(budget-1,024) − d_q(top-5)**.
E1's mechanism predicts **DiD > 0 for both claims** (A gains relative to B once text is equalised).

1. **Primary Tier 2 estimate:** pooled DiD for answer F1 = equal-weight mean over datasets of the per-dataset mean
   DiD; 95% CI from a stratified bootstrap (queries resampled within dataset, 2,000 resamples, seed 7).
   Complete cases only (queries with all 8 jobs successful); the number dropped is reported.
2. **Reading rule** (exploratory language only): CI > 0 → "carries over"; CI < 0 → "opposite"; otherwise
   "inconclusive". The minimum detectable DiD (α = 0.05, power 0.8, observed SD) is reported next to it, so an
   inconclusive result is read against what 200 queries could detect.
3. **Secondary:** per-dataset Δ under each operating point and DiD (paired bootstrap, 2,000, seed 7); the same for EM;
   the same DiD for retrieval coverage on the same 200 queries (does the sample reproduce E1's reversal?).
4. **Retrieval–answer link:** Pearson correlation of coverage and F1; mean F1 by lenient hit.
5. **Diagnostics:** status counts, finish reasons (MAX_TOKENS = truncation), served model versions, rate of
   "unanswerable" replies, token usage.

## Known limits (stated in advance)
- 50 queries per dataset gives low power; E1's H3 shows that 2-point differences need > 1,000 paired queries.
  Tier 2 can detect only large answer-level effects.
- Answer F1 against short gold spans penalises verbose but correct answers; Qasper and CUAD golds are long or
  multi-span, so their F1 levels are not comparable across datasets (DiD is within-dataset).
- One generator, one sample: model-family generality is not tested.

Code: `src/ragmv/analyze_generation.py` (tested on synthetic data with a known effect and a null).
