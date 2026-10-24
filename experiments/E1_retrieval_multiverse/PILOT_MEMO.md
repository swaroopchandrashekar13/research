# E1 pilot memo — EXPLORATORY (not confirmatory evidence)

*2026-10-18 · run `runs/pilot-exploratory-20261018` · analysis `analysis/pilot-exploratory-20261018`*

> **Status of these numbers.** They come from the **exploratory split** (20% of documents per dataset). The
> pre-registration (`research/preregistration.md`) fixed H1–H3 and their thresholds *before* this run. This memo
> may inform runtime and sample-size planning only. **It must not be cited as confirmation of any hypothesis**,
> and no hypothesis, threshold or analysis choice may now change without a logged deviation marked "post-pilot".

## What ran
- 4 datasets × 16 chunkings × 16 BM25 configurations × 9 operating points × 3 metrics; exploratory queries: SQuAD 1,184 · COVID-QA 248 · CUAD 248 · Qasper 460.
- Wall-clock ≈ 3 min total on 4 vCPU (Qasper 104 s); peak RSS ≈ 350 MiB. Analysis ≈ 20 s.
- Code: the manifests are flagged dirty because `analyze.py`/`figures.py` were untracked new files during the run.
  Later runs record the exact `git status`. (The commit identifier originally cited here is unresolvable; the
  original history is no longer available and the identifier was removed on 2026-10-24, see
  `docs/repair/HASH_REDACTIONS.md`.)

## Exploratory results (as computed by `ragmv.analyze`)
| ID | Estimate | 95% CI | Pre-registered threshold | Would-be verdict |
|---|---:|---|---:|---|
| H1 | 70.5 pp | [61.3, 81.5] | 20 pp | supported |
| H1b | 29.6 pp | [15.1, 35.8] | 10 pp | supported |
| H2 | dataset η² largest in 98.7% of replicates (η²: dataset 0.58, budget 0.08, metric 0.04, retriever 0.01) | — | 95% | supported |
| H3 | 84.9% of universes need n > 500 (median 1,323) | — | > 50% | supported |

All five pre-specified H1 sensitivity analyses gave 62–73 pp. Full tables: `analysis/pilot-exploratory-20261018/results.md`.
Figures: `analysis/pilot-exploratory-20261018/figures/`.

## Sanity checks performed
1. **The reversal is not driven by one dataset.** P1 count-matched: fixed-512 wins in 95% (SQuAD), 97% (COVID-QA),
   12% (CUAD), 100% (Qasper) of universes. Budget-matched: fixed-128 wins in 67%, 70%, 72%, 50%.
2. **H1b mechanism holds.** Paragraph-256 chunks average 174–199 words vs ~250 for fixed-256, so count-matching
   gives paragraph chunking 20–30% less text.
3. **Counter-evidence is visible, not hidden.** Under budget-matching, Qasper still favours fixed-512 in 22% of
   universes (long evidence paragraphs, median 156 words, reward large chunks under strict containment).
4. Unit tests (47) cover metric arithmetic, protocol exactness, sign conventions and a constructed-artefact
   recovery test (`tests/test_ragmv_analysis.py`).

## Problems found and how they were handled
| Problem | When | Handling |
|---|---|---|
| Budgets smaller than the chunk size force truncation of the top chunk (degenerate; biases H1) | Smoke test, before pilot | Logged pre-run deviation; admissible budgets B ≥ max(W_A, W_B); full set kept as sensitivity (e) |
| `/usr/bin/time` missing, first pilot launch failed before doing work | Pilot launch | Peak RSS recorded via `resource` inside the manifest; failed launch logs deleted (no results produced) |
| First dumbbell figure plotted only "A wins" and hid count-matched B-wins | Figure review | Switched to net share (A − B) with a zero line |

## What a reviewer will say first — and what we need
**"Of course giving one side four times more text helps; H1 is near-tautological."** Partly fair. Our answers:
(a) budget-matching did *not* have to reverse the verdict (Qasper shows it need not); the size and dataset
dependence of the reversal are empirical; (b) the contribution only matters if **published chunking comparisons
actually use count-matched protocols**. We therefore need **a protocol audit of the chunking literature**: for each
paper, record whether comparisons fix top-k, fix a token budget, or are unclear. That needs full-text access (blocked
here) or the researcher downloading the PDFs. **This is the highest-value next literature task.**

**"Retrieval metrics are not answer quality."** Tier 2 (RQ5) tests whether the reversal carries over to generated
answers. Estimated cost ≈ $46 with the Batch API for Claude Haiku 5.5 + Sonnet 5.5 (≈ $2 Haiku only). This uses an
assumed 1.35 tokens/word, to be replaced by exact token counts before approval.

## Planning implications (legitimate uses of a pilot)
- Confirmatory runtime ≈ 4× pilot ≈ 12–15 min CPU. No compute constraint.
- H3's pilot estimate (median required n ≈ 1,300) means CUAD (996 confirmatory queries) will be under-powered for
  2-point effects. That is a finding to report, not a reason to change the design.
