# POST-HOC SENSITIVITY (2026-10-24): character-based metrics — not pre-registered

**Why.** The pre-registration (`research/preregistration.md` §2.2) defines hit_strict, hit_lenient and coverage over
*characters*. The stored results were computed over *words*: `ragmv.data` converts each gold character span to the
half-open interval of `\S+` words it overlaps (a boundary inside a word extends the span to that whole word; a span
of whitespace only is dropped), and `ragmv.evaluate` scores word overlap. This was found and disclosed on 2026-10-24
(`research/ERRATA_preregistrations.md`). The pre-registered results are **not** replaced; this directory quantifies
how much the definition matters.

**How.** Rankings and selected intervals were not stored, so BM25 retrieval was **re-executed** (new execution,
2026-10-24, CPU; `python -I -m ragmv.posthoc study1`). Before attributing any difference to the metric, selection
equivalence was verified: the re-executed word scores (float16) and word counts equal the stored arrays for all
**85,275,648** stored values (`selection_equivalence.json`: 0 mismatches; retrieval depths equal the manifests). The
same selections were then scored three ways and analysed with the unchanged pre-registered code and thresholds
(`python -I -m ragmv.analyze --label POSTHOC`):

| Variant | Definition |
|---|---|
| `word64` | the stored word metric without float16 rounding (isolates the storage-precision effect) |
| `char` | literal characters: a retrieved chunk covers its text's characters; whitespace between two separately retrieved chunks is covered by neither |
| `char_nows` | characters excluding whitespace |

**Result** (H estimates in percentage points; CIs from 1,000 joint replicates; `summary.json`):

| Variant | H1 | H1b | H2 (dataset η²; largest in) | H3 (> 500; median n) | Universe verdicts changed vs stored (of 24,960) |
|---|---|---|---|---|---|
| stored (word, float16) | 71.1 [64.8, 81.9] supported | 26.7 [15.4, 33.9] supported | 0.614; 100% supported | 85.4%; 1,256 supported | — |
| word64 | 71.1 [64.8, 81.9] supported | 26.7 [15.4, 33.9] supported | 0.614; 100% supported | 85.4%; 1,256 supported | 0 |
| char | 70.4 [63.9, 80.3] supported | 24.2 [13.5, 30.7] supported | 0.590; 100% supported | 85.5%; 1,275 supported | 965 (779 hit_strict, 149 hit_lenient, 37 coverage); 0 sign reversals |
| char_nows | 71.1 [64.9, 81.9] supported | 26.2 [15.0, 33.2] supported | 0.620; 100% supported | 85.4%; 1,263 supported | 197 (0 hit_strict); 0 sign reversals |

All five H1 sensitivity analyses stay above the 20-point threshold under every variant. **Reading:** no
pre-registered hypothesis verdict depends on the word-versus-character definition or on float16 storage for Study 1;
estimates move by at most 2.5 percentage points (H1b, literal characters), and individual universe verdicts change
mainly for strict containment under the literal character definition. This is a post-hoc sensitivity analysis and
does not alter the pre-registered results.

The variant score arrays (44 MB) are not committed; they are regenerated deterministically by the commands above.
