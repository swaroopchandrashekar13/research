## 1. Data
| Dataset | Domain | Documents | Queries used | Gold evidence |
|---|---|---|---|---|
| SQuAD 2.0 dev | Wikipedia | 35 articles (paragraphs joined by blank lines) | answerable only (5,928) | union of annotator answer spans |
| COVID-QA | Biomedical papers | 147 | all with spans (2,019) | answer span(s) |
| CUAD v1 test | Contracts | 102 | answerable only (1,244) | all answer spans (multi-span allowed) |
| Qasper v0.3 dev+test | NLP papers | 697 (section names + paragraphs, blank-line separated) | questions with ≥ 1 evidence paragraph located in the text | evidence paragraphs from all annotators; "FLOAT SELECTED" (table/figure) evidence dropped |

**Splits.** Within each dataset, documents are randomly assigned to *exploratory* (20%) or *confirmatory* (80%) with
seed `20261018`. Queries follow their document. The retrieval corpus is always the full dataset. Exploratory data is
used only for debugging, runtime estimation and the power pilot. **No hypothesis, threshold or analysis choice may
change after looking at confirmatory data.**

## 2. Design (the multiverse)

### 2.1 Chunkings (the objects of the claims): 16 configurations
"Word" = a maximal non-whitespace run (`\S+`). Every chunk is a contiguous character interval of the document.
| Family | Parameters | Rule |
|---|---|---|
| fixed | W ∈ {64, 128, 256, 512}; overlap ∈ {0, 25%} | sliding windows of W words, stride W − overlap |
| sentence | W ∈ {64, 128, 256, 512} | pack whole sentences (rule-based splitter) up to W words; an over-long sentence falls back to fixed windows |
| paragraph (structure-aware) | W ∈ {64, 128, 256, 512} | pack whole paragraphs (blank-line boundaries) up to W words; an over-long paragraph falls back to the sentence rule |

### 2.2 Evaluation factors (the "nuisance" choices)
| Factor | Levels |
|---|---|
| Retriever (16) | BM25 variant {Lucene, BM25+} × k1 {0.9, 1.5} × b {0.4, 0.75} × tokenisation {English stop-words + Snowball stemming, lowercase only} (library `bm25s` 0.2.13) |
| Selection protocol | **count-matched**: top-k chunks, k ∈ {1, 3, 5, 10}; **budget-matched**: highest-ranked chunks until B words, the last chunk truncated to fit exactly, B ∈ {128, 256, 512, 1024, 2048}. Duplicate text from overlapping chunks counts against the budget |
| Metric | **hit_strict** = 1 if some gold span lies entirely inside the union of retrieved text; **hit_lenient** = 1 if some gold span has ≥ 50% of its characters retrieved; **coverage** = max over gold spans of the fraction of its characters retrieved |
| Dataset | the four above |

A *universe* is one combination of (dataset, retriever, protocol, operating point, metric).
**Admissible budgets:** for a claim comparing chunk sizes W_A and W_B, budget-matched universes use only
B ≥ max(W_A, W_B), so neither side is forced to truncate its top-ranked chunk. All budgets are kept for sensitivity
analysis (e). Example: P1 (128 vs 512) has 4 × 16 × (4 + 3) × 3 = **1,344 universes**.

Exploratory metric (not used for H1–H3): chunk-level reciprocal rank RR@10 (first chunk that fully contains a gold span).

### 2.3 Claims (pairwise contrasts A vs B; Δ = metric(A) − metric(B))
| ID | Role | A | B |
|---|---|---|---|
| P1 | **primary** | fixed-128 (no overlap) | fixed-512 (no overlap) |
| S1 | secondary | fixed-W vs fixed-2W (no overlap), W ∈ {64, 128, 256} | |
| S2 | secondary | fixed-W with 25% overlap | fixed-W without overlap, all W |
| S3 | secondary | paragraph-W | fixed-W (no overlap), all W; **S3-256** is the designated instance for H1b/H2 |
| S4 | exploratory | sentence-W | fixed-W (no overlap) |

## 3. Hypotheses (fixed before any data was examined)
For each universe, Δ_u gets a 95% paired-bootstrap percentile CI (2,000 query resamples, seed 7).
**Verdict:** *supports A* (CI > 0), *supports B* (CI < 0), or *inconclusive*.
Uncertainty in any rate over universes comes from 1,000 joint query-bootstrap replicates: queries are resampled within
each dataset, and all universes are recomputed on the same resample.

| ID | Statement | Supported if | Falsified if |
|---|---|---|---|
| **H1** (primary) | For P1, the share of universes supporting fixed-512 is **≥ 20 percentage points lower** under budget-matched than under count-matched selection | point estimate ≥ 20 pp **and** 95% CI excludes 0 | 95% CI upper bound < 20 pp |
| H1b | For S3-256, the share of universes supporting paragraph-256 is **≥ 10 pp higher** under budget-matched than under count-matched selection. Mechanism: paragraph packing yields shorter chunks, so count-matching gives it less text | point estimate ≥ 10 pp and CI excludes 0 | CI upper bound < 10 pp |
| H2 | For S3-256 under budget-matched selection, in a main-effects ANOVA of Δ_u on {dataset, retriever, budget level, metric}, **dataset has the largest η²** | dataset η² largest in ≥ 95% of bootstrap replicates | another factor's η² is larger in ≥ 50% of replicates |
| H3 | For S2 and S3 under budget-matched selection, the paired n needed to detect \|δ\| = 0.02 (α = 0.05 two-sided, power 0.8; n = ((1.96 + 0.8416)·σ_d/0.02)², σ_d = SD of per-query differences) **exceeds 500 in more than half of universes** | proportion of universes > 0.5 | proportion ≤ 0.5 |

All other analyses are **exploratory** and will be labelled as such.

## 4. Analysis plan
1. Verdict shares per claim × protocol (tables and specification-curve figures).
2. H1/H1b: difference in shares with bootstrap CI.
3. H2: main-effects decomposition with η² = SS_factor / SS_total per bootstrap replicate, computed analytically from group means; for this balanced full-factorial design this equals statsmodels OLS type-II sums of squares (verified by unit test `test_eta_squared_matches_statsmodels_on_balanced_design`).
4. H3: required n per universe from the confirmatory per-query differences.
5. **Sensitivity analyses** (pre-specified): (a) Benjamini–Hochberg FDR 5% within claim instead of raw CIs; (b) excluding SQuAD (few, very long articles); (c) only the "default" retriever (Lucene, k1 = 1.5, b = 0.75, stemmed); (d) **document-cluster bootstrap** (resample documents, keep all their queries), because queries are nested in documents (added 2026-10-18 before any run, after counting confirmatory documents per dataset: SQuAD 28, COVID-QA 118, CUAD 82, Qasper 558).
   (e) all budgets including B < max(W_A, W_B).
   Within each joint-bootstrap replicate, verdicts use normal-approximation CIs (mean ± 1.96·SD/√n) to avoid a nested bootstrap; point-estimate verdicts use the percentile bootstrap.
6. Multiplicity: H1 is the single primary test. Secondary results are reported with that label. Universes are not independent, so shares describe *this designed multiverse*, not a population of all possible designs.

## 5. Tier 2 — generation (exploratory, conditional on approval and API access)
Generators `claude-haiku-5-5` and `claude-sonnet-5-5`. 200 confirmatory queries per dataset (seeded sample). Claims P1
and S3-256. Count k ∈ {3, 5}; budget B ∈ {512, 1024}. Two samples per query: sampling parameters cannot be fixed on
these models, so stochasticity is estimated, not removed. Answer metric: SQuAD-style token F1 against gold answer
strings. The cost will be measured with token counting on the real prompts and approved **before** any call.

## 6. Compute and reproducibility
CPU only (4 vCPU, 15.7 GiB; `env/environment.json`). Every run writes a manifest: git SHA, config hash, seeds, package
versions, wall-clock and exit status. Failed runs are kept. Per-query results are stored as compressed arrays
(`experiments/E1_*/runs/`, git-ignored if large); aggregate tables and figures are committed and are regenerated by
scripts only.

## 7. Threats to validity (known in advance)
- **Construct:** span-based retrieval metrics are proxies for answer quality (RQ5 tests part of this). Qasper evidence
  matching may drop queries non-randomly.
- **Internal:** rule-based sentence splitting errors; the truncation rule in budget-matched selection; word counts
  instead of model tokenizer counts.
- **External:** lexical retrieval only (dense retrievers unavailable here), English only, four datasets, extractive
  QA style.
- **Statistical:** universes share queries and are correlated; bootstrap-over-queries handles within-dataset
  dependence but not the choice of datasets.

## 8. Deviations log
| Date | Deviation | Reason | Affects confirmatory results? |
|---|---|---|---|
| 2026-10-18 | Budget-matched universes restricted to B ≥ max(W_A, W_B); full budget set moved to sensitivity analysis (e) | Smoke test (60 exploratory SQuAD queries, no hypothesis-relevant statistics computed) showed that B < W forces truncation of the top chunk, a degenerate operating point that is implied by the design and would bias H1 towards support | No — made before any pilot or confirmatory run |
| 2026-10-18 | Added sensitivity analysis (d), document-cluster bootstrap | Queries are nested in few documents for SQuAD (28 confirmatory articles) | No — made before any run |
| 2026-10-18 | **Post-pilot clarification:** §5.3 wording changed from "statsmodels OLS" to the analytic η² actually implemented (numerically identical for this balanced design); sensitivity-analysis CIs use the full 1,000 joint-bootstrap replicates | Code–document consistency check before freezing | No — same estimands, same thresholds |
| 2026-10-18 | **Post-confirmatory bug fix:** sensitivity analysis (d) computed its point-estimate verdicts with the document-cluster bootstrap, but its CI silently used query-level resampling. Fixed (`joint_bootstrap(..., clusters=)`, new test). Diff of all results before/after: one field changed, (d) CI [64.8, 81.9] → [63.8, 82.0] | Found by checking that (d)'s CI was identical to the main CI | Only that sensitivity CI; no hypothesis estimate or verdict changed |
| 2026-10-19 | **Tier 2 (exploratory) redesigned before any Tier 2 call:** generator changed from Claude Haiku/Sonnet to a Gemini Flash-class model (the API key available to the researcher; exact model ID recorded per row); scope reduced to fit free-tier quota: 50 seeded confirmatory queries per dataset, chunkings fixed-128/fixed-512/paragraph-256/fixed-256 (claims P1, S3-256), operating points k = 5 and B = 1,024, default retriever, temperature 0 and one sample (seed 7). Metric unchanged (SQuAD-style EM/F1) | Researcher has a Gemini key, not an Anthropic one; free-tier daily limits | No — Tier 2 is exploratory and was not run before this change |
| 2026-10-19 | **Tier 2 pre-run amendment:** generator fixed to `gemini-3.6-flash` with thinking level *minimal*; the served model version is recorded per row; analysis plan pre-specified (`experiments/E2_generation/ANALYSIS_PLAN.md`, DiD estimand) | A model probe showed that the ID `gemini-3.5-flash` is served by `gemini-3.6-flash` (alias), so the requested ID alone does not identify the model; default thinking spent 137 tokens on one easy question and counts toward the 256-token output cap (truncation risk on long contexts). Probe: 11 calls (6 on the first sampled SQuAD job prompt, 5 on a one-word test prompt); outputs inspected for format only and not recorded as results | No — made before any Tier 2 job was run |
| 2026-10-19 | **Tier 2 generator changed to a local open-weight model:** Qwen3-4B (official Q4_K_M GGUF, Hugging Face commit `bc640142`, SHA-256 checked) via llama.cpp (llama-cpp-python 0.3.36, CPU, 4 threads), greedy decoding (temperature 0, top-k 1), thinking disabled with an empty think block, max 256 output tokens. Design, sample, prompt text and analysis plan unchanged. The 21 Gemini rows are kept as an aborted run and not analysed | The key's free tier allows 20 requests/day (~80 days for 1,600 jobs); researcher chose a free local model over billing (decision 022). Model chosen on a 16-job benchmark on the **exploratory** split only: Qwen2.5-1.5B was 3x faster but answered 'unanswerable' with the answer present in 3/16 jobs and grew more verbose with longer contexts, which would bias the context-length contrast | No — made before any job of the local run |
| 2026-10-19 | **Tier 2 run moved to Google Colab (GPU), as a fresh complete run** (`runs/qwen3-4b-colab`): same model file, prompts, code and analysis plan; `--n-gpu-layers -1`; the hardware is recorded in every row. The CPU run (`runs/qwen3-4b-20261019`, 197 jobs, stopped) is kept and not analysed | Researcher's request to run it on their own Colab; the GPU cuts ~15-20 h to ~1-2 h. A fresh run avoids mixing CPU and GPU greedy outputs within one analysis | No — made before any Colab job |
| 2026-10-19 | **Tier 2 hardware: the researcher's Apple-silicon Mac (Metal) instead of Colab**, run `runs/qwen3-4b-mac` via `experiments/E2_generation/run_mac.sh`; same model file, code, prompts and plan; hardware recorded per row. If both a Colab and a Mac run are ever completed, the Mac run is the analysed one (fixed now, before either exists) | Colab's session limits; the Mac is free and local | No — made before any Mac job |
| 2026-10-19 | **Tier 2 hardware: Kaggle notebook GPU** (`runs/qwen3-4b-kaggle`, `experiments/E2_generation/notebook_tier2.py`); replaces the Mac choice. Rule fixed now, before any Tier 2 run on researcher hardware exists: the Kaggle run is analysed; any other complete run (Mac, Colab, PC via `run_tier2.py`) is reported only as a hardware-robustness check | Researcher's choice of platform; same model file, code, prompts and plan; hardware recorded per row | No — made before any Kaggle job |
| 2026-10-19 | **Kaggle run naming and CPU fallback:** the notebook builds llama-cpp-python with CUDA (fix for Kaggle's `CUDA::cuda_driver` discovery) and verifies GPU offload; if that fails it uses a CPU build. CPU and GPU rows go to separate runs (`qwen3-4b-kaggle-gpu` / `qwen3-4b-kaggle-cpu`) and are never pooled. The analysed run is the **first** of the two to reach 1,600 jobs; the other, if ever completed, is a hardware-robustness check. Rows are pushed hourly to branch `tier2-results`, so a run can span several sessions | Researcher's Kaggle CUDA build failed (`CUDA::cuda_driver` not found); model, quantisation, prompts and decoding are identical on both paths, so only speed differs | No — rule fixed before any Kaggle row exists |
