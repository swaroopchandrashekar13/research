# Repair report — research repository (branch `swaroop-fix`, 2026-10-24)

Scope: repair of the defects listed in the repair request (24 audit IDs) and of newly found issues, with validation of
the repaired tree. The audit ZIP/reports were not supplied; the register (`REPAIR_REGISTER.md`) states how each ID
was interpreted. Nothing was published: no pull request, release, Zenodo upload, manuscript submission or paid API
call. History was not rewritten.

Companion files: `REPAIR_REGISTER.md` (all IDs, evidence, tests, status) · `VERIFICATION.md` (statistical comparison
matrix and display regeneration) · `CLAIM_TRACE.md` and `CLAIM_TRACE_MACROS.md` (claim verification) ·
`ARTIFACT_VALIDATION.md` · `HASH_REDACTIONS.md` · `REPRODUCIBILITY.md` · `PROTECTED_SHA256.txt` ·
`statistical_verification.json` · `../../research/ERRATA_preregistrations.md`.

## 1. Decision: READY AFTER SPECIFIED FIXES
The code, analyses, displays and manuscript are internally consistent and verified to the extent this environment
allows: every stored statistic was reproduced by the original code and by an independent implementation, BM25
retrieval was re-executed with exact agreement, Tier 2 inputs and scores were rebuilt exactly, all 115 result
macros trace to their sources, and the canonical manuscript builds cleanly. Publication should wait for these
owner actions:

1. **Licence (release blocker, LIC-001).** Decide how the gold-answer strings and model answers in
   `experiments/E2_generation/runs/**/generations.jsonl` are distributed (source licences incl. SQuAD's CC BY-SA
   ShareAlike, or keep them private and publish only per-query metrics). Do not deposit on Zenodo before this.
2. **Citations (NEW-005).** None of the 39 cited works is read in full (L3), which the project's own protocol requires
   before citing; Smucker et al. (2007) identity is also unconfirmed. Read the works whose content the paper relies
   on and confirm each characterisation.
3. **Security (NEW-008).** Confirm that the Gemini API key once pasted into a chat (see `docs/guides/ACCESS_AND_SETUP.md`)
   was revoked. No secret is in the repository or its accessible history.

Documented limitations that remain after those fixes (they do not block publication if stated, as the manuscript now
does): dense retrieval and generation were not re-executed; the character-metric effect on the dense arm is
unquantified; H5 is Monte-Carlo sensitive; the protocol audit is single-coded by an AI assistant (AUDIT-001); the
timing of the analysis plans cannot be verified because the original history is gone.

## 2. Status grid
| Area | Status | Evidence |
|---|---|---|
| Source/import integrity | PASS | `compileall` + import of every module; ruff F/E9 clean; clean-clone installs on Python 3.12 and 3.13 |
| Unit and integration tests | PASS | 136 passed, 3 skipped (optional Gemini/llama.cpp SDKs) with verified data; 128 passed, 11 skipped without data; 0 errors |
| Data checksums | PASS | 5 archives re-downloaded and matched; 3 extracted members digest-checked; loaders' inputs verified |
| Statistics | PASS | same-code recomputation exact (2,063 fields); independent implementation 13/13; post-hoc checks change no verdict; **H5 Monte-Carlo sensitivity disclosed** |
| Experiment reruns | PARTIAL | BM25 re-executed exactly (86,941,188 stored values); Tier 2 prompts/EM/F1 rebuilt exactly; dense retrieval and generation BLOCKED (GPU) |
| Display regeneration | PASS | macros, 13 tables, 4 figures, refs.bib regenerated in isolation; deterministic PDFs; differences limited to the listed corrections |
| Manuscript build | PASS | both variants, clean directory: exit 0, 23 pages, 0 errors, 0 undefined references/citations, 0 duplicate labels, 0 overfull boxes; pages inspected |
| Claim traceability | PARTIAL | 115/115 macros recomputed; assertion matrix supported; related-work characterisations not verified against full texts |
| Historical Git provenance | BLOCKED | original history unavailable; all unresolvable references removed (scan 0); chronology now stated as unverifiable |
| Bibliography | PARTIAL | schema valid; 38/39 identities confirmed; 0 entries at L3 |
| Licences | BLOCKED | descriptions reconciled and checked against publisher/author cards; owner decision needed for third-party strings |
| Full clean-checkout reproduction | PARTIAL | fresh clones reproduce tests, validation, analyses and displays; GPU stages not reproducible here |

GitHub CI: the workflow file exists; whether and how it ran on GitHub is reported in the hand-off message, not here
(a workflow file is not evidence that CI ran).

## 3. How contradictory instructions were resolved
| Instruction(s) | Conflict | Resolution |
|---|---|---|
| Remove hashes inside historical manifests, result metadata and pre-registration copies **vs** keep run manifests/outputs and retain protected bytes | both cannot hold | Minimal textual redaction of only the commit-valued `git` fields and two places in the Study 1b plan; every other byte kept and checked; before/after digests in `HASH_REDACTIONS.md`; originals remain in history |
| "scrub historical Git history" **vs** "History rewriting: NOT authorized" | | History not rewritten; references removed from files only |
| "delete a file merely if an old hash appears in it" | would delete evidence | No file was deleted for containing a hash |
| "Never store/record real current Git provenance" **vs** "record code-content identities" | | New work records SHA-256 content digests (code, inputs, configuration), never commit IDs; this report states the branch, not a commit |
| "Never preserve existing job IDs in historical logs" | the only job IDs are deterministic record keys of 2,019 primary-evidence rows | Not removed; flagged for the owner (NEW-009) |
| Alternative draft: "Do not preserve … and deleting it" | | `manuscript/main_revised.tex` deleted (SHA-256 `1ae287f240da31ddc871462d6f52436efe926e4a5789678ca295eb02ba43a0cf`; recoverable from history) |
| Correct section errors while preserving the plan's bytes | | Erratum file; plans not edited for these |
| "Do not report historical dates as recorded/reported" | | The manuscript no longer states freeze dates or chronology; historical summaries keep their own date headers |
| Work on `swaroop-fix` | the session also designates another branch | All work is committed on the local branch `swaroop-fix`. Pushing was refused by the session's permission system (external write), so nothing has been pushed; the owner pushes when ready |

## 4. Scientific changes (no threshold, estimand or verdict changed)
- Metrics are word-based (MAN-001): described as such, with a dated correction; post-hoc character rescoring of the
  identical re-executed BM25 selections changes no hypothesis verdict (H1 71.1→70.4, H1b 26.7→24.2 pp under literal
  characters).
- Bootstrap schemes, seeds and BH family described as implemented (STAT-001); equal-weight MDE added (STAT-002).
- H5 sensitivity (NEW-001): inconclusive with the pre-registered seed (19.4 pp), 21.5–24.3 pp with nine other seeds.
- E2: inconclusive F1 interactions no longer read as "no effect"; the contrary EM result and the positive coverage
  result are kept (CLAIM-002). Causal wording qualified (CLAIM-001). H5b amendment kept and disclosed.
- Study 1 dumbbell drawn from the analysed shares (≤ 0.009 shift).

## 5. Protected evidence
Baseline: SHA-256 of all 365 tracked files recorded before any change. Protected set: run directories (manifests,
queries, NPZ, logs, generation logs, chunk files, upload digests), original analysis outputs, the analysis plans and
E2 analysis plan, `env/environment.json`, the original requirement files, the audit coding and candidates and the
search log — 284 files.

| Result | Files |
|---|---|
| byte-identical to baseline | 254 |
| changed only in redacted `git` lines (verified line by line against the baseline) | 29 |
| changed only at the two redacted references (`research/preregistration_study1b.md`) | 1 |
| deleted | 0 |

Non-protected changes: 53 files edited (code, tests, docs, manuscript sources and generated displays, metadata), 1
deleted (`manuscript/main_revised.tex`, as directed), 88 added (new code, tests, tools, repair documents, post-hoc
outputs, identity-check records, CI). `tools/validate_artifacts.py` checks the current protected digests
(`PROTECTED_SHA256.txt`).

## 6. Security and hygiene
Scanned all tracked files and decompressed gzip members (the accessible history is a single commit): no credentials
or private keys; no absolute personal paths (only platform paths such as `/kaggle/working` in notebooks); no file
> 1 MB; no pickle loading (`np.load(..., allow_pickle=False)` everywhere). Notebook tokens no longer enter URLs, config
or logs. `run_mac.sh` no longer pipes a remote installer into a shell. Owner action: NEW-008.

## 7. Commands, exit codes and counts (validation environment: Python 3.13.17, Linux, 4 CPUs)
| Command | Exit | Result |
|---|---|---|
| baseline: `python -m pytest -q tests` (README verbatim, no install) | 2 | 5 collection errors (`ragmv` not importable) |
| baseline: `PYTHONPATH=src pytest --ignore tests/test_research_tools.py` | 0 | 52 passed, 11 skipped |
| fresh clone, README commands verbatim, Python 3.13 / 3.12 | 0 / 0 | 128 passed, 11 skipped each; validator 0; bibliography 0 |
| `RAGMV_DATA_ROOT=… pytest -q` | 0 | 136 passed, 3 skipped |
| `python -I -m ragmv.fetch --root <scratch>` / `--verify-only` | 0 / 0 | 5 archives, 3 members |
| `ragmv.analyze` / `analyze1b` / `analyze_generation` on stored runs + `tools/compare_results.py` | 0 | 975 / 449 / 639 fields identical |
| `tools/independent_stats.py` | 0 | 13/13 |
| `ragmv.posthoc study1` / `study1b` | 0 / 0 | 0 equivalence mismatches |
| `ragmv.analyze --label POSTHOC` × 3 | 0 | no verdict changes |
| `tools/validate_artifacts.py --data-root …` | 0 | 89 passed, 0 failed, 29 notes |
| `manuscript/build_displays.py --compare manuscript` (after promotion) | 0 | identical |
| `manuscript/build_pdf.py` | 0 | see status grid |
| `tools/trace_claims.py` | 0 | 115/115 |
| `tools/redact_git_refs.py --check`, `tools/scan_hex_refs.py` | 0, 0 | 0 commit fields; 0 unclassified |
| `tools/check_bibliography.py` | 0 | 88 entries (L1 57, L2 31) |
| `cffconvert --validate` | 0 | valid (schema 1.2.0) |
| `tools/verify_bib_identity.py` | 0 | 37/39 automatic + 1 manual (ACL Anthology) |

## 8. Second-pass review of this report
- Every PASS above cites an executed command with its exit code; reruns that were not executed are PARTIAL/BLOCKED.
- Counts reconcile: 254 + 29 + 1 = 284 protected files; 85,275,648 + 1,665,540 = 86,941,188 re-executed values;
  965 = 779 + 149 + 37 changed universe verdicts (character metric); 975 + 449 + 639 = 2,063 recomputed fields.
- No unresolved historical commit identifier remains in active material (scan exit 0); this report contains none.
- Limitations stay visible: dense/generation reruns, H5 Monte-Carlo sensitivity, single-coded audit, unverifiable
  chronology, citations below L3, licence decision.

## 9. Continuation checkpoint
- Branch `swaroop-fix`, **local only** (the push was refused by the session's permission system; the container is ephemeral, so push or bundle the branch before the session ends); working tree clean after the final commit.
- Protected baseline: digests of all 365 baseline files are reproducible from the first commit of the branch's
  history (`git ls-tree`/`git show` of the parent of the first repair commit); current protected digests in
  `PROTECTED_SHA256.txt`.
- Code and tree identity of the validated state: see §10.
- Pending (owner): LIC-001 decision; L3 reading of cited works; NEW-008 key revocation; NEW-009 job-ID decision;
  AUDIT-001 blind coding; GPU reruns (dense retrieval, generation) if full reproduction is wanted.
- Next commands for a GPU environment: `python -I -m ragmv.run1b --dataset <d> --split confirmatory --out <new dir>`
  (then `tools/compare_results.py` against the stored analysis); Tier 2: `notebook_tier2.py` with
  `RAGMV_CODE_REF=<tag>`.

## 10. Identity of the validated tree
Validated at **2026-10-24T19:22:26Z** (UTC), immediately before the final commit of this report.

| Identity | SHA-256 |
|---|---|
| Code content of `src/ragmv/*.py` (`ragmv.integrity.source_digest`) | `2c01088e43b3652b9334275a010c411f7723faed1d0a92d73bd351e4fd66bd91` |
| All tracked files except this report (sorted path, NUL, file SHA-256 per line) | `878054038f289e7e4a630d1df94cf66b8e5ff0b32a3d830b0bfa84ad18b45b13` |

Recompute: `python -I -c "import sys; sys.path.insert(0,'src'); from ragmv.integrity import source_digest; print(source_digest()['sha256'])"` and
`git ls-files | grep -v '^docs/repair/REPAIR_REPORT.md$' | sort | while read f; do printf '%s\0%s\n' "$f" "$(sha256sum "$f" | cut -d' ' -f1)"; done | sha256sum`.
The final validation sequence (§7: pytest 136/3, validator 89/0, trace 115/115, displays 0 differences, PDF build 0,
scans 0) ran on exactly this tree; the only later changes are to this report (this section, and the push statements
in §3 and §9, corrected after the push was refused).
