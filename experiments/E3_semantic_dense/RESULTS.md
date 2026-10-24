# Study 1b (E3) confirmatory results — semantic chunking and dense retrieval

*2026-10-19 · pre-registration `research/preregistration_study1b.md` v1.0 · run `runs/confirmatory-kaggle-gpu`
(Kaggle Tesla T4, clean tree; bge-m3 revision `5617a9f6` fp16) · analysis `analysis/confirmatory-kaggle-gpu` · 9,253
confirmatory queries (SQuAD 2.0 4,744 · COVID-QA 1,771 · CUAD 996 · Qasper 1,742), never seen by the pilot.*

> **Provenance note (2026-10-24).** The project commit identifiers originally cited for the freeze and the run are
> unresolvable (the original version history is no longer available) and were removed; see
> `docs/repair/HASH_REDACTIONS.md`. The freeze chronology therefore cannot be independently verified. The decision
> log this summary originally referred to is not in the repository.

## Integrity checks (before reading results)
- All manifests `ok`; query lists equal the confirmatory split (the same 9,253 queries as Study 1).
- Fixed-chunk BM25 scores equal Study 1's stored confirmatory scores exactly (all datasets, W = 128/256/512).
- Semantic chunks partition every document, never exceed 512 words, and are **identical to the pilot's chunks**
  (embeddings reproduced exactly across two GPU sessions); BM25 scores recompute exactly from the stored chunks.
- The pre-registered analysis rerun locally reproduces the Kaggle `results.json` exactly.

## Pre-registered hypotheses
| ID | Statement (short) | Estimate | 95% CI | Threshold | Verdict |
|---|---|---:|---|---:|---|
| **H4** (primary) | Share of universes favouring the **shorter arm** (semantic breakpoint vs fixed-W) rises from count- to budget-matched | **55.4 pp** (9.4% → 64.8%) | [50.8, 63.1] | 20 pp | **Supported** |
| H4b | Same for clustering chunks | 64.4 pp (6.9% → 71.3%) | [56.5, 68.3] | 10 pp | Supported |
| H5 | With dense retrieval, share favouring fixed-512 drops (Study 1's H1) | 19.4 pp (25.0% → 5.6%) | [16.7, 41.7] | 20 pp | **Inconclusive** (estimate just below the threshold) |
| H5b *(post-pilot amendment)* | With dense retrieval, share favouring fixed-128 (shorter arm) rises | 58.3 pp (33.3% → 91.7%) | [45.1, 64.6] | 20 pp | Supported |

H4 sensitivity analyses (all pre-specified): BH-FDR 54.3 pp · without SQuAD 48.0 pp [42.7, 58.3] · document-cluster
bootstrap 58.7 pp [50.0, 63.3] · all budgets 53.7 pp [49.7, 60.9] · BM25 only 61.1 pp [57.2, 72.5] · dense only
49.8 pp [39.1, 58.1]. The conclusion holds under every one, and with both retrievers.

## What it means (plain language)
- **"Semantic chunking beats fixed-size chunking" is a protocol artefact in the same way as Study 1's chunk-size
  verdicts.** Against 128-word fixed chunks, breakpoint chunking wins 60% of universes at equal top-k and 8% at equal
  text (fixed wins 75%); clustering chunks win 53% vs 0% (fixed 97%). Against 512-word chunks the direction flips,
  because there the semantic chunks are the shorter arm. What decides the verdict is **which arm returns more text**,
  not chunk "semanticity".
- **The effect holds with a dense retriever** (H4 dense-only 49.8 pp; H5b 58.3 pp). With bge-m3 large chunks are
  weaker even at equal k, so H5's fixed-512 share has little room to fall — the pilot predicted this floor, and H5 is
  inconclusive, not falsified. Reported as pre-registered.

## Limits
One embedding model; the clustering defaults (λ = 0.5, threshold 0.5) let clusters fill the 512-word cap with
bge-m3 (disclosed before the run); four English extractive-QA datasets; retrieval metrics, not answers (Tier 2 found
no carry-over to answer F1 for a 4B reader); shares describe this designed multiverse.
