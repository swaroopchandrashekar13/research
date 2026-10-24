# Report 4 — Research Roadmap and First Practical Actions

*Phase 0 · 2026-10-18*

## 1. Phases and approval gates

| Phase | Goal | Exit criterion | Gate (your approval needed) |
|---|---|---|---|
| 0 Background & landscape | Assess your work; map directions | Reports 1-4 delivered (this) | — |
| 1 Novelty verification | Raise the closest papers to L3; confirm or kill the gap | Written gap statement with full-text citations | **G1: lock topic** |
| 2 Problem statement | Formal problem, RQs, hypotheses, scope, success/failure criteria | `research/problem_statement.md` reviewed by you | — |
| 3 Pre-registered design | Variables, factors, datasets, splits, tests, thresholds, compute budget | `research/preregistration.md` frozen with a git tag | **G2: methodology and any spend** |
| 4 Smoke test | End-to-end on a tiny subset; metric unit tests; leakage checks | Green CI, logged smoke run | — |
| 5 Confirmatory runs | Full multi-seed runs with provenance | Raw logs + manifest per run | — |
| 6 Analysis | Scripts → tables and figures generated from raw logs only | Reproducible `make results` | — |
| 7 Manuscript | Write the paper only after results exist | Compiled PDF; citations gated at L3 | — |
| 8 Three-reviewer audit | Novelty, rigor, clarity reviews; fix and re-run | Audit memo with every item resolved or justified | **G3: submission** |
| 9 Submission & PhD use | Preprint, venue submission, SoP, outreach | Submitted; outreach list | (outreach needs your approval) |

**Exploratory vs confirmatory.** The MVEs in Report 3 are *exploratory*: they test the pipeline and give rough effect
sizes for power analysis. The hypotheses, thresholds and analysis plan are frozen in Phase 3 **before** confirmatory
runs. Results from the MVE are never reported as confirmation.

## 2. Two timeline options. You choose (D5).

| | Option 1: apply this cycle (Dec 2026 – early 2027) | Option 2: apply next cycle (late 2027) — **my recommendation** |
|---|---|---|
| Research artifact at application time | Exploratory MVE + technical report / early preprint | Full preprint and a submitted (possibly accepted) paper |
| Letters | Existing referees | Plus one researcher who has seen your study |
| Best targets | European advertised positions (rolling); a few well-fitting programmes | Full US + EU + pan-European set |
| Risk | Thin research evidence; rushed work | One more year; mitigated by applying to rolling EU positions as soon as the preprint exists |

Under Option 2, a realistic schedule at **8-10 hours per week** (please tell me your real number):

| Weeks (from approval) | Work |
|---|---|
| 1-2 | Phase 1: read closest papers in full; G1 decision |
| 3-4 | Phases 2-3: problem statement and pre-registration; G2 |
| 5-6 | Phase 4: harness, tests, smoke runs (retrieval stage) |
| 7-12 | Phase 5-6: retrieval multiverse, then generation stage |
| 13-16 | Phase 7: manuscript draft → arXiv preprint |
| 17-18 | Phase 8: audit, revisions; target venue submission |
| Rolling | Apply to EU positions once the preprint is live; prepare the late-2027 cycle |

## 3. First practical actions

**Mine (can start immediately once unblocked):**
1. Read BERGEN, the TOSEM RAG design-decisions paper and the 2026 silent-failure study in full, then update
   `literature/evidence_matrix.md` to L3. **Blocked:** arxiv.org, aclanthology.org and sciencedirect.com are denied
   by the environment's network policy.
2. Write the Phase 1 structured literature search script (arXiv + Semantic Scholar) with saved raw responses.
   **Blocked:** same policy.
3. Draft the C5 problem statement in plain-language and academic versions, for you to critique.

**Yours (decisions, Section 5) — about 30 minutes.**

**Yours (learning exercises).** These build the independent judgement a PhD supervisor will test.
- **E1. Critique one paper (90 min).** Read Qu et al., "Is Semantic Chunking Worth the Computational Cost?" (Findings of
  NAACL 2025). Write one page answering: What exactly is the claim? How many queries support it? Is there a
  significance test or confidence interval? Which single evaluation choice, if changed, could most plausibly flip the
  conclusion? Save it as `docs/exercises/E1.md`.
- **E2. Blind re-score (45 min).** Without looking at my scores, independently score C3, C5 and C2 using the criteria described in Report 3. Record your scores and compare your three largest disagreements with the rankings in that report.
- **E3. Falsifiability (20 min).** In five sentences, state one C5 hypothesis and the exact result that would falsify it.
- **E4. Paired tests (40 min).** Explain, in your own words and with a toy example of 10 queries, why comparing two RAG
  configurations *on the same queries* needs a paired test, and what goes wrong with an unpaired one.
- **E5. Supervisor-fit sketch (later).** For two groups in Report 2 §4, read one recent paper each and write two
  sentences on what your study would add.

## 4. Resource requests

| Need | Why | How to grant |
|---|---|---|
| Network access to `arxiv.org`, `export.arxiv.org`, `api.semanticscholar.org`, `api.crossref.org`, `openreview.net`, `aclanthology.org` | Full-text verification (L2/L3) and a reproducible search | Environment settings → Network access → add to Allowed domains (keep "Allow package managers" ticked). See https://code.claude.com/docs/en/cloud-environments#network-access |
| Network access to `huggingface.co` (and its CDN hosts, if prompted) | Public datasets and small open models for CPU experiments | Same setting |
| LLM access for the generation stage (optional for the MVE) | Generator and judge runs | Either an API key as an environment secret with a spend cap you set, or confirmation to stay local-only with small open models on CPU (slower, smaller scope) |
| Your hardware | Whether a Mac or GPU is available outside this container | Tell me |

Current container: 4-core x86 CPU, 15.7 GiB RAM, **no GPU**, no LaTeX (installable). Details in `env/environment.json`.

## 5. Decisions I need from you

| ID | Decision | My recommendation |
|---|---|---|
| D1 | Confirm this workspace is for the researcher in Report 1 and that portfolio claims are accurate | — |
| D2 | Keep this repository **public** (sanitised, as now) or make it private (then internal specifics could live here) | Make it private until the preprint, then publish code and data |
| D3 (**G1 pre-check**) | Direction to verify in Phase 1: C5 (+C3 next), C3, C2, or something else | C5 then C3 |
| D4 | Grant network domains and choose LLM access (API with cap vs local-only) | Domains yes; local-only for the MVE, decide on API at G2 |
| D5 | Application cycle and weekly hours | Option 2, 8-10 h/week |
| D6 | Confirm no employer code, data or confidential material will be used, and check your employment contract for publication/IP clauses | Clean-room, public data only |

## 6. Key risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phase 1 finds the C5 gap already filled | Medium | Pre-defined fallbacks (C3, then C8 or sharpened C2) in Report 3 §6 |
| Network policy keeps blocking primary sources | Medium | You grant domains, or you download PDFs and add them to the repo for me to read |
| Scope creep in the multiverse (combinatorial explosion) | High | Fix the factor grid in pre-registration; retrieval stage first; sampled multiverse |
| Time pressure leads to cutting rigor | Medium | The approval gates; Option 2 timeline |
| Maintaining independent research ownership | Medium | You write the problem statement and statement of purpose yourself; a mentor can critique and suggest improvements. Follow the intended publication venue's research-integrity and disclosure policies. |
