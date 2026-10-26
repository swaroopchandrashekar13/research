# Post-hoc plan: bounding the effect of the two underfilled Study 1b selections

*Written 2026-10-25T18:32Z, before the analysis below was run. Post-hoc; not part of the study plans.*

**Trigger.** The budget-underfill census (`tools/budget_underfill_census.py`) found two budget-matched selections
below their budget in the stored runs, both in the Study 1b confirmatory run, dense retriever, Qasper, budget 2,048:
one query under `fixed-128` (1,880 words) and one under `fixed-256` (1,789 words). The manifests record ranking depths
of 36 and 28 against corpora of 19,124 and 9,721 chunks, so more text existed than was ranked. Dense retrieval cannot
be re-executed here (GPU embeddings of the full corpus), so the corrected scores cannot be computed.

**Bound.** Adding retrieved text can never lower hit_strict, hit_lenient or coverage (the metrics are monotone in the
selected positions), so each affected score lies between its stored value and 1.0.

**Settings (fixed now).**
1. Copy the stored run directory to scratch; change nothing but the two cells: for the affected query, the dense
   retriever and the B2048 operating point, set all three metrics to 1.0 (upper bound). The lower bound is the stored
   run itself.
2. Run `python -I -m ragmv.analyze1b --label CONFIRMATORY` on the copy with the planned settings (2,000 verdict
   resamples, seed 7; 1,000 joint replicates, seed 11).
3. Compare every field with the stored `results.json` (`tools/compare_results.py`, floats exact to 1e-12).
4. Report every changed field and every changed verdict, whatever the direction. If no hypothesis verdict changes at
   the upper bound, the stored verdicts hold for any corrected value of these two selections.

No original file is modified; the corrected run is not computed and nothing is relabelled as confirmatory.
