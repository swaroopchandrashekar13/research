# Verification report (2026-10-25)

Current state of the repository, what was checked, how, and with what result. Supporting reports in this
directory: `STATISTICAL_VERIFICATION.md`, `CLAIM_MATRIX.md` (with `CLAIM_TRACE_MACROS.md`), `CITATION_SUPPORT.md`,
`ARTIFACT_VALIDATION.md`, `BUDGET_UNDERFILL_CENSUS.md`, `HASH_POLICY.md`, `RIGHTS_AND_ATTRIBUTION.md`,
`FILE_INVENTORY.md` and `REPRODUCIBILITY.md`.

## Current state (2026-10-25)

- The work is in local commits on the branch `Swaroop-fix-1`. Nothing was pushed, no pull request was opened, no
  remote workflow was triggered, and nothing was released, published or uploaded (no Zenodo deposit).
- All results below come from **local** runs. The CI workflow (`.github/workflows/ci.yml`) was parsed but has not run
  for this state; a CI result shown for an earlier state of the repository says nothing about this one.
- The repository is meant to move to another host. No file refers to the current repository; the notebooks take the
  repository URL as a setting.

## Environment

| | |
|---|---|
| Machine | Linux 6.18.44 (fc-v153), glibc 2.39, 4 vCPU, no GPU |
| Python | 3.13.17 in a virtual environment whose packages equal `env/validation/lock-py3.13.txt` except `wrapt` 2.5.1 (lock: 2.5.2rc1; a dependency of `formulaic`); the direct pins equal `requirements/core.txt` and `requirements/test.txt` |
| TeX and tools | pdfTeX 1.40.25 (TeX Live 2023/Debian), latexmk 4.83, poppler 24.02.0, fonts-inter 4.0+ds-1, ruff 0.16.9 |
| Data | the four datasets downloaded from their publishers and verified against `data/MANIFEST.yaml` (archives and extracted members) |

This is not the historical environment (`env/validation/README.md`).

## Status

| Area | Status | Evidence |
|---|---|---|
| Syntax and imports | PASS | `ruff` (syntax and pyflakes rules) clean on all Python; every package module imports |
| Unit tests | PASS | without data 234 passed, 12 skipped; with data 242 passed, 4 skipped (skips: data absent, optional Gemini/llama.cpp SDKs, a check that needs an uncommitted tree) |
| Integration tests | PASS | synthetic runs, resume and interruption, notebook bootstrap, release package; BM25 retrieval reproduction against the stored Study 1 run; the release package's own suite: 230 passed, 16 skipped |
| Dataset integrity | PASS | all four downloads and extracted members match `data/MANIFEST.yaml`; splits, query lists, gold spans, chunk partitions and Tier 2 inputs rebuilt from the data (98 structural checks, 0 failed) |
| Statistical calculations | PASS | same-code recomputation: 0 differences for E1, E3 and E2, the E3 pilot and the three post-hoc analyses; independent recomputation: 22 of 22 checks (`STATISTICAL_VERIFICATION.md`). Exception: the stored E1 pilot (exploratory) differs in 8 interval bounds |
| Experiment reproduction | PARTIAL | BM25 retrieval re-executed: every stored score and word count reproduced (85,275,648 Study 1 and 1,665,540 Study 1b values); dense retrieval and generation not re-executed (GPU) |
| Output regeneration | PASS | 23 displays regenerated identical (tables, figures by coordinates and bytes, macros, bibliography); census and underfill bound reproduce their records |
| Manuscript builds | PASS | named and anonymous variants: 23 pages each, 0 undefined references or citations, 0 overfull boxes, 1 underfull box; the anonymous PDF has no author, identifying text, metadata or links; rendered pages inspected |
| Claim-to-result traceability | PASS | 122 of 122 result macros recomputed from their sources; `CLAIM_MATRIX.md` |
| Git and content provenance | PARTIAL | 294 protected files byte-identical; run identities removed by owner decision, so all 16 historical records have incomplete provenance; original version history unavailable |
| Bibliographic identity | PARTIAL | 36 of 39 cited works confirmed against primary records; 3 unreachable |
| Citation claim support | PARTIAL | 4 citation uses read in full (L3); the rest at abstract or record level (`CITATION_SUPPORT.md`) |
| Licensing and archive preparation | PARTIAL | rights inventory, metrics-only package (21 of 21 checks), consistent metadata; owner decisions open (below) |
| Full end-to-end reproducibility | PARTIAL | a clean checkout reproduces everything except the GPU steps |

## What was run

Two clean checkouts (fresh clones, no local files, the datasets supplied from a verified scratch copy):

- **Run A**, before the last code changes: the full pipeline below.
- **Run B**, the final code: tests, validation, policy and metadata checks, census and bound, protected digests, and
  the release package built and verified, which reruns the three analyses and the independent checks from the
  package. The code changes between A and B are the validator's provenance-gap rule and one test.

| Step | Command | Result |
|---|---|---|
| Tests | `python -m pytest -q -rs` without and with `RAGMV_DATA_ROOT` | exit 0 (A, B) |
| Lint | `ruff check --select E9,F src tests tools manuscript experiments literature` | exit 0 |
| Validation | `python -I tools/validate_artifacts.py [--data-root data/raw]` | exit 0; structure 54 / 98 passed, 0 failed; provenance 0 complete, 16 incomplete (B) |
| Data | `python -I -m ragmv.fetch --verify-only`; loader inputs checked | exit 0 |
| Hash policy / hex scan | `tools/check_hash_policy.py`, `tools/scan_hex_refs.py` | 275 historical files, 0 violations; 0 unclassified tokens |
| Bibliography / metadata | `tools/check_bibliography.py`, `tools/check_release_metadata.py` | 88 entries (L1 54, L2 31, L3 3); 0 failures, 2 notes (no ORCID iD, no DOI) |
| Recompute E1, E3, E2 | `ragmv.analyze`, `ragmv.analyze1b`, `ragmv.analyze_generation` into new directories; `tools/compare_results.py --inputs-against` | 975, 449, 639 fields identical; 0 different; 0 input mismatches (A; again from the package in B) |
| Recompute pilots | same, E1 and E3 pilot runs | E3: 449 identical; E1: 967 identical, **8 different** (exit 1, explained in `STATISTICAL_VERIFICATION.md`) |
| Post-hoc re-execution | `ragmv.posthoc study1`, `study1b`; three POSTHOC analyses; both summary tools | exit 0; all stored scores and word counts reproduced; analyses (1,002 fields each) and summaries equal the committed ones |
| Independent statistics | `tools/independent_stats.py` | 22 of 22 PASS; output equals `statistical_verification.json` |
| Census and bound | `tools/budget_underfill_census.py`, `tools/underfill_bound.py` | equal to the committed records (B) |
| Claims | `tools/trace_claims.py` | 122 of 122 macros |
| Displays | `manuscript/build_displays.py --compare manuscript` | 0 differences |
| Manuscript | `manuscript/build_pdf.py --render-pages` | exit 0; see above |
| Protected evidence | digests of the 294 listed files | 0 changed |
| Release package | `tools/stage_release.py build`, `verify --source . --data-root data/raw --recompute` | 447 files; 21 of 21 checks PASS (B) |

The validation environment (below) is not the historical one, and CI has not run for this state.

## Protected evidence

`PROTECTED_SHA256.txt` lists 294 files: the original runs, the original and post-hoc analysis outputs, the analysis
plans, the historical environment and requirement records and the audit records. Every listed file was hashed
before any change in this review and again on the clean checkout: all 294 are byte-identical, and the list itself
matches those digests. No protected file was changed. Four protected files (the three `UPLOAD_SHA256` markers and
one note in `research/preregistration_study1b.md`) name an earlier ledger that is no longer in the repository
(`HASH_POLICY.md`).

## Open limitations (all disclosed in the manuscript or the reports)

- **Provenance of the historical runs is incomplete** (16 records): configuration fingerprints, code identities,
  model revisions, prompt and upload digests were removed by the owner and cannot be checked against the runs.
- **Not re-executed:** dense retrieval (bge-m3) and answer generation (Qwen3-4B) need a GPU. Their stored outputs are
  validated and analysed, and BM25 retrieval is re-executed exactly; whether the dense and generated outputs would
  reproduce on other hardware is not known.
- **Chronology:** the timing of the analysis plans relative to the runs cannot be verified (original version history
  unavailable); the manuscript makes no claim about it.
- **E1 pilot analysis:** recomputation differs from the stored file in 8 sensitivity-interval bounds (exploratory; see
  `STATISTICAL_VERIFICATION.md`).
- **Measurement:** metrics are word-based, not character-based as the plans state; the character-based rescoring
  covers the BM25 selections only.
- **H5** is inconclusive at the planned seed and would meet the support rule with nine other seeds; it is reported as
  unresolved.
- **Two underfilled stored selections** (dense, Qasper, 2,048 words): the post-hoc bound changes no verdict.
- **Audit:** single-coded by an AI research assistant; no independent coding or reliability statistic.
- **Citations:** 4 citation uses verified in full (L3); the others at the abstract or record level, and 3 identities
  could not be confirmed from a primary record (`CITATION_SUPPORT.md`). The reference list shows the verification
  level of every entry below L3.

## Owner decisions and actions before release

1. **Third-party strings** in the generation logs: deposit the metrics-only package (ready) or decide to redistribute
   the strings under the datasets' terms (`RIGHTS_AND_ATTRIBUTION.md`). Neither removes them from the history of the
   current repository; creating the new repository from a tree without the logs would give a history without them.
2. **Zenodo licence field** for the combined package (`docs/guides/ZENODO.md`), and the Apache-2.0 notice question
   for COVID-QA-derived material.
3. **ORCID iD** (optional): record it with `tools/check_release_metadata.py --set-orcid`; it is never filled in for
   you.
4. **Before submission:** read in full the works cited below L3 (at least the six L1 uses) and remove the verification
   notes from the reference list; have the audit coded independently if any prevalence claim is to be made.
5. **CI:** after the move, run the workflow once on the new host (manually with `with_data` and `release_gate` for the
   full gate); no remote CI result exists for this state.
6. **Credentials:** no credential pattern occurs in the files or in the history available here. That does not show
   that any key used in earlier work (for example the Gemini key of the aborted runs) was never exposed elsewhere; if
   in doubt, revoke it.
