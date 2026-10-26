# Archiving the study on Zenodo (DOI) with your ORCID iD

Zenodo gives a deposit a DOI. Files of a published record can never be changed or deleted; its metadata (authors,
description, licence) can be edited later. Prepare and check everything first, try the sandbox, then publish.

## Choose what to deposit (owner decision)

| Route | What is archived | Status |
|---|---|---|
| **A. Upload the metrics-only package** (recommended until the decision below is made) | The zip built by `tools/stage_release.py`: code, plans, run manifests, per-query results, analyses, manuscript sources, and the answer-generation records as per-row metric values without answer or response text | Ready to build and verify |
| B. GitHub release integration on the new repository | Everything in the repository at that release, including the generation logs with gold answer strings and model answers (third-party text, see `LICENSE-DATA.md`) | Needs the owner's decision on redistributing those strings under the datasets' terms (attribution; ShareAlike for SQuAD) |

Neither route removes anything from the history of the current repository or from copies already distributed;
see `docs/remediation/RIGHTS_AND_ATTRIBUTION.md`.

## 1. ORCID iD (optional, free)

1. Register at <https://orcid.org/register> (or sign in) and copy your 16-character iD (form `0000-0000-0000-000X`).
2. Record it in both metadata files; the tool checks the iD's check digit and writes nothing if it is wrong:
   `python -I tools/check_release_metadata.py --set-orcid <your iD>`
3. In Zenodo, link the iD to your account (Zenodo → Settings → Linked accounts → ORCID), so the record shows it.

Never enter an iD that is not yours or a made-up one; without an iD the record is still valid.

## 2. Build and check the package (route A)

From a clean, committed working tree:

```bash
python -I tools/check_release_metadata.py                   # metadata agree; notes for missing ORCID/DOI
python -I tools/stage_release.py build --out W/ragmv-release.zip
python -I tools/stage_release.py verify W/ragmv-release.zip --source . --data-root data/raw --recompute \
    --report W/package-verification.md                     # every check must PASS (the rerun takes ~7 min)
md5sum W/ragmv-release.zip; sha256sum W/ragmv-release.zip  # Zenodo shows the MD5 of each uploaded file
```

`verify` reads the zip itself: allowed files only, `SHA256SUMS` complete, metrics files with exactly the allowlisted
fields, no answer or response string, no run of dataset text, no private paths or credentials; `--recompute`
extracts it and reruns the validation, tests and analyses from the package alone.

## 3. Deposit

1. Optional dry run on <https://sandbox.zenodo.org> (separate account; its DOIs are not real).
2. <https://zenodo.org> → log in (GitHub, ORCID or e-mail) → **New upload**.
3. Upload `ragmv-release.zip`; compare the MD5 Zenodo shows with yours.
4. Metadata, copied from `.zenodo.json` / `CITATION.cff`: resource type *Software*; title; creator
   *Chand J C, Swaroop* (with the ORCID iD if linked); description; keywords. Licence: the package combines MIT code,
   CC BY 4.0 project material and third-party identifiers (`LICENSE-DATA.md`); choose how to state this in Zenodo's
   licence field (owner decision) and keep `LICENSE-DATA.md` as the authoritative description.
5. **Publish** creates the version DOI and the concept DOI (all versions).

## 4. After publishing

- Cite the version DOI in the manuscript's reproducibility section and add `doi:` to `CITATION.cff`
  (`python -I tools/check_release_metadata.py` checks its form).
- A corrected package becomes a new version of the same record (Zenodo → the record → **New version**).
- Identify the archived material by its DOI and by `SHA256SUMS`, not by commit identifiers.
