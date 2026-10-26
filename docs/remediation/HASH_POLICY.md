# Hash and identifier policy

## Owner decision

Machine-readable identities were removed from the historical evidence at the owner's request and are **not
recovered**: the commit identifiers the runs and plans cited (the original version-control history is not
available, so they could not be resolved), configuration fingerprints, prompt digests, model revisions recorded by
the runs, model-file digests, upload-archive digests and the hexadecimal identifiers of the GPU build log. No
recovery index is kept. Validators report these values as removed by owner decision, never as verified.

## What is kept, and why

| Kept | Where | Purpose |
|---|---|---|
| Dataset download and member digests | `data/MANIFEST.yaml` | `ragmv.fetch` refuses data whose bytes differ |
| Model pins | `src/ragmv/dense.py` (bge-m3 revision), `src/ragmv/generate.py` (Qwen3-4B GGUF revision and file SHA-256) | new runs load exactly these models; the manuscript cites them as the code's pins |
| Protected-file digests | `docs/remediation/PROTECTED_SHA256.txt` | any change to protected evidence fails validation |
| Identities written by new runs | `code_sha256`, `inputs_sha256`, `config_sha256` of runs created with the current code | provenance of new runs is complete and checkable |
| Dataset question IDs | query lists, logs, results | they are identifiers, not hashes, even where they look hexadecimal (SQuAD, Qasper) |
| Package digests | `SHA256SUMS` in the release package | integrity of the archived files |

## Removed-value markers

Removed values were replaced by these exact strings:

| Marker | Replaces |
|---|---|
| `redacted: historical digest removed` | configuration and prompt digests |
| `redacted: unresolvable historical Git commit` | commit identifiers in run records |
| `@[revision removed]` | the revision inside a served model name |
| `redacted: model revision removed` | the model revision in job metadata |
| `redacted: model file digest removed` | the model-file SHA-256 in job metadata |
| `redacted: upload-archive digest removed 2026-10-25 (docs/remediation/HASH_POLICY.md)` | the digest in the three `UPLOAD_SHA256` files |
| `[hash removed]` | hexadecimal identifiers in the build log |

Markers are accepted only where `ragmv.provenance` allows them: the registered historical runs
(`HISTORICAL_RUNS`, bound by run directory and each record's start time), the analysis outputs derived from them, and
the three registered upload files. A marker anywhere else is a structural failure.

## Consequences

The historical runs are structurally valid, but their provenance is **incomplete**: whether a stored run used the
code, configuration, model revision and prompts that the repository now contains cannot be confirmed from the run
records. The stored per-query results are still checked for structure, recomputed into identical analyses, and, for
BM25 retrieval and the Tier 2 prompts, rebuilt from the data (see `VERIFICATION.md`). The removed values remain in
the Git history of the repository where it is available; nothing was rewritten.

## Checks

- `python -I tools/check_hash_policy.py`: historical files contain no hash value other than dataset question IDs;
  markers occur only where allowed; the code pins are present (read-only; exit 1 on a violation).
- `python -I tools/validate_artifacts.py`: structure (PASS/FAIL) and provenance (COMPLETE/INCOMPLETE) are reported
  separately; `--require-provenance` makes incomplete provenance fail (a release gate).
- `python -I tools/scan_hex_refs.py`: every hexadecimal token in active material is classified; an unclassified one
  fails.
