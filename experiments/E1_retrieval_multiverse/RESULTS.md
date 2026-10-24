# E1 confirmatory results

*2026-10-18 · pre-registration v1.0 (`research/preregistration.md`) · run `runs/confirmatory-20261018` (all four
manifests: status `ok`, empty `git status`) · analysis `analysis/confirmatory-20261018`*

> **Provenance note (2026-10-24).** The original version-control history of this project is no longer available. The
> commit identifiers this summary and the run manifests originally cited cannot be resolved and were removed (see
> `docs/repair/HASH_REDACTIONS.md`). The freeze chronology stated in the pre-registration therefore cannot be
> independently verified. Content digests of the surviving files are recorded in `docs/repair/`.

**Data:** confirmatory split (80% of documents, never seen by the pilot): SQuAD 2.0 4,744 · COVID-QA 1,771 ·
CUAD 996 · Qasper 1,742 = **9,253 queries**. 16 chunkings × 16 BM25 configurations × admissible operating
points × 3 metrics. Runtime 5.8 min on 4 vCPU; analysis 1.6 min.

## Pre-registered hypotheses

| ID | Statement (short) | Estimate | 95% CI | Threshold | Verdict |
|---|---|---:|---|---:|---|
| **H1** (primary) | Share of universes favouring fixed-512 over fixed-128 drops from count- to budget-matched | **71.1 pp** | [64.8, 81.9] | 20 pp | **Supported** |
| H1b | Share favouring paragraph-256 over fixed-256 rises from count- to budget-matched | 26.7 pp | [15.4, 33.9] | 10 pp | Supported |
| H2 | Dataset explains the most variance in Δ (S3-256, budget-matched) | dataset η² 0.61 (budget 0.10, retriever 0.04, metric 0.03); largest in 100% of replicates | — | ≥ 95% | Supported |
| H3 | > 50% of S2/S3 universes need > 500 paired queries to detect a 2-point difference | 85.4% (median n = 1,256) | — | > 50% | Supported |

**H1 sensitivity analyses** (all pre-specified): BH-FDR 68.0 pp · without SQuAD 61.5 pp [53.2, 74.8] · default
retriever only 70.8 pp [64.6, 85.4] · document-cluster bootstrap 69.7 pp [63.8, 82.0] · all budgets 74.2 pp
[68.3, 84.8]. The conclusion holds under every one.

## What the numbers say (plain language)
- **Comparing chunk sizes at a fixed top-k reverses the conclusion you get at a fixed amount of text.** At equal
  k, 512-word chunks beat 128-word chunks in 79% of universes, and 128 never wins. At an equal word budget, 128
  beats 512 in 81% of universes, and 512 wins in only 8%. The same reversal appears for every adjacent size pair
  (S1-128, S1-256).
- **Structure-aware (paragraph) chunking is under-rated by top-k comparisons**, because its chunks are 20–30% shorter
  than their nominal size. Its advantage over fixed windows rises from 50% to 77% of universes once text is equalised.
- **Overlap (S2) is protocol-insensitive**: equal chunk sizes on both sides means no text imbalance (consistent with
  the mechanism).
- **Which dataset you evaluate on matters far more than retriever tuning** (η² 0.61 vs 0.04).
- **Studies of a few hundred queries are under-powered for small differences in this design**: detecting a 2-point
  difference for overlap or structure claims needs about 1,150–1,500 paired queries; ~85% of universes need more
  than 500. (Qualified 2026-10-24: this is a statement about this multiverse's variance, not a survey of study sizes.)
- **Metric unit.** All metrics are computed on words (gold character spans mapped to the words they overlap), not on
  characters as the plan states; a post-hoc character-based rescoring changes no hypothesis verdict
  (`analysis/posthoc-charmetric-20261024/`).

## Per-dataset breakdown (P1, share of universes favouring each side)
| Dataset | Count: 128 / 512 | Budget: 128 / 512 |
|---|---|---|
| SQuAD 2.0 | 0% / 100% | 83% / 0% |
| COVID-QA | 0% / 89% | 100% / 0% |
| CUAD | 0% / 26% | 97% / 0% |
| Qasper | 0% / 100% | 44% / 31% |

## Exploratory observations (not pre-registered; hypotheses for follow-up)
1. **In Qasper the metric decides the verdict, even at equal budget.** Strict containment favours fixed-512 in 92%
   of universes; lenient hit and coverage favour fixed-128 in 67%. Qasper's gold evidence is whole paragraphs (median
   156 words), which small chunks rarely contain whole. The relevance definition is therefore a second evaluation
   artefact. Follow-up: pre-register it as a factor in Study 1b.
2. CUAD shows the weakest count-matched preference for large chunks (26%), consistent with its templated,
   keyword-heavy clause queries. Needs a mechanism check before any claim.

## Deviations from the pre-registration
See `research/preregistration.md` §8 (this summary originally said §9; corrected 2026-10-24): two pre-run changes (admissible budgets; cluster sensitivity), one post-pilot
wording clarification, and one **post-confirmatory bug fix** in sensitivity (d)'s CI. That fix changed one field
(CI [64.8, 81.9] → [63.8, 82.0]) and no hypothesis estimate or verdict.

## Limits on what this establishes
- **Lexical retrieval only.** Dense retrievers were unavailable (Hugging Face blocked). The mechanism (text imbalance
  under count-matching) does not depend on the retriever, but magnitudes may.
- **Retrieval metrics, not answers.** Whether the reversal changes LLM answer quality is RQ5 (Tier 2, not yet run).
- **Shares describe this designed multiverse**, not all possible evaluation designs. Universes share queries.
  Within-replicate verdicts use normal-approximation CIs (pre-registered shortcut), and the H1 CI is not centred on
  the point estimate, a known property of bootstrapping a thresholded statistic.
- **Significance depends on practice.** The finding matters to the extent that published chunking comparisons use
  count-matched protocols. That protocol audit of the literature is not done yet; it needs full texts.
- Four English extractive-QA datasets; word counts stand in for tokenizer counts.
