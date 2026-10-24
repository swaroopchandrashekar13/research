# Coding conventions (added while coding; applied to every paper)

*2026-10-19 · these refine, but do not change, the fields in `PROTOCOL.md`. Each convention was written down the first
time a case needed it, and earlier codes were re-checked against it.*

1. **Version coded.** The published (venue) version when available, otherwise the latest arXiv version; recorded in
   `version_coded`. Page numbers refer to that PDF.
2. **`selection_protocol` for rank metrics.** Metrics computed over a ranked list of chunks with a cutoff (Recall@k,
   Hit@k, nDCG@k, DCG@k, F1@k, top-k context for generation) compare arms at an equal *number* of chunks → `fixed_k`.
   A rank metric without a stated cutoff (e.g., reciprocal rank of the first relevant chunk) is also count-based but
   has no k → `other`, with a note. Document-level ranking after aggregating chunk scores (e.g., MaxP) → note it;
   the paper's chunk-level comparison decides the code.
3. **`chunk_length_differs_between_arms`.** `yes` when arms are defined by different chunk sizes or the paper reports
   different mean lengths; `no` when lengths are matched by design and reported; `unclear` when lengths are neither
   fixed by design nor reported.
4. **`reports_retrieved_text_amount`.** `yes` only if the amount of retrieved/packed text (tokens, words, characters)
   is reported per condition or as a function of the compared factor. Reporting chunk counts, index size or the
   chunk-size parameter alone is `no`.
5. **`uncertainty_reported`** refers to the chunking comparisons. Tests reported only for other factors (e.g.,
   embedding models) are recorded in `notes`, not in this field. Words like "significantly" without a test are `none`.
6. **`headline_claim`** is a verbatim quotation of the paper's main chunking conclusion (abstract or conclusion).
