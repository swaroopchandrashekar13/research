# Protocol audit of chunking comparisons — protocol

*Version 1.0 · 2026-10-18*

## Why
Study 1 shows that chunking verdicts reverse between count-matched (fixed top-k) and budget-matched (equal text)
comparisons. That finding matters in practice only if published comparisons actually use count-matched protocols
without controlling the amount of retrieved text. This audit measures how often they do.

## Research question
Among published empirical comparisons of chunking strategies or chunk sizes for retrieval or RAG (2023–2026), what
share (a) compares at a fixed number of retrieved chunks, (b) controls or reports the amount of retrieved text,
(c) reports uncertainty (CIs or significance tests), and (d) evaluates on more than one dataset?

## Sample
- **Frame:** papers in `candidates.csv`. These were identified by the logged web searches #7, #16–18 (session 1) and the
  session 4 searches before any full text was read. Every candidate meeting the inclusion criteria is coded. Nothing
  is dropped for its result.
- **Extension:** backward citation chaining from the included papers' related-work sections (one hop), logged in
  `candidates.csv` with `source = citation:<key>`. Papers enter only by meeting the inclusion criteria.
- **Inclusion:** (1) empirical; (2) compares ≥ 2 chunking strategies or ≥ 2 chunk sizes; (3) reports a retrieval or
  RAG answer metric; (4) full text available to us.
- **Exclusion:** our own study; pure method papers with no comparison against another chunking; non-English.

## Coding scheme (one row per paper in `coding.csv`)
| Field | Values |
|---|---|
| `selection_protocol` | `fixed_k` · `fixed_budget` · `both` · `other` · `unclear` |
| `k_values` | as reported, or `NA` |
| `reports_retrieved_text_amount` | `yes` (tokens/words per condition reported) · `no` |
| `chunk_length_differs_between_arms` | `yes` · `no` · `unclear` (e.g., LLM chunkers produce different mean lengths) |
| `n_datasets` | integer |
| `n_queries_per_dataset` | integer or range |
| `uncertainty_reported` | `none` · `seeds_only` · `CI` · `significance_test` |
| `metric_type` | `retrieval` · `answer` · `both` |
| `headline_claim` | one sentence quoting the paper's main chunking conclusion, with page number |
| `evidence_location` | section/page where the protocol is described |
| `coder`, `confidence` | initials; `high`/`medium`/`low` |

## Reliability
The researcher independently codes a random 30% of included papers (seed 20261019) **before seeing the mentor's
codes**. We report Cohen's κ for `selection_protocol` and `reports_retrieved_text_amount`, and resolve
disagreements by discussion, logged in `disagreements.md`. κ < 0.6 means the codebook is revised and every paper is
re-coded.

## Output
Shares with Wilson 95% CIs; a table of papers whose headline claim compares arms with different chunk lengths at
fixed k (candidate artefacts). We will **not** claim any specific paper's conclusion is wrong. We report only whether
its protocol leaves the text-amount confound uncontrolled.
