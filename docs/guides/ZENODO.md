# Archiving this repository on Zenodo (DOI)

Zenodo archives a **GitHub release** and gives it a DOI. Archived files can never be changed or deleted; the record's
metadata (authors, description, licence) can be edited later. So: get the repository right first, then release.

## Before the first release
1. **Repository and history.** The current repository is `https://github.com/swaroopchandrashekar13/research`. The
   project's original version history is no longer available, so no earlier commit can serve as a timestamp for the
   pre-registrations; do not cite historical commit identifiers anywhere (they were removed on 2026-10-24, see
   `docs/repair/HASH_REDACTIONS.md`). The archived snapshot is identified by its release, its DOI (once Zenodo issues
   one) and the SHA-256 content digests in `docs/repair/`.
2. **Author:** Swaroop Chand J C (cited as "Chand J C, S."). Add your ORCID iD to `CITATION.cff` and `.zenodo.json`
   only when you have one (free at <https://orcid.org>); never add a placeholder.
3. **Release blockers.** Resolve the items listed under "Release blockers" in `docs/repair/REPAIR_REPORT.md`
   (in particular third-party text in `generations.jsonl`, see `LICENSE-DATA.md`) before making a public release.
4. Check the metadata: `cffconvert --validate` (if installed) and
   `python -I -c "import json; json.load(open('.zenodo.json'))"`; `python -I tools/validate_artifacts.py`.

## Enable Zenodo (one time, in the browser)
1. <https://zenodo.org> → **Log in** → **Log in with GitHub** (authorise the Zenodo app).
2. User menu (top right) → **GitHub** (<https://zenodo.org/account/settings/github/>). Click **Sync now** if the
   repository is not listed, then switch it **On**.
   Optional dry run first on the test site <https://sandbox.zenodo.org> (same steps; its DOIs are not real).

## Make the release (this creates the DOI)
1. GitHub → the repository → **Releases** → **Draft a new release**.
2. Tag: e.g. `v0.9.0` (pre-submission snapshot) or `v1.0.0` (the version that matches the arXiv paper); target the
   default branch. Title and notes: one paragraph on what the snapshot contains.
3. **Publish release.** Within a few minutes Zenodo archives it and emails you; the DOI is on the record page.

## After the release
- **Two DOIs:** the *version DOI* (this exact snapshot) and the *concept DOI* (all versions; resolves to the latest).
  Cite the version DOI in the paper so readers get the exact code and results behind it.
- Add the DOI badge (record page → DOI badge → Markdown) to `README.md`, the DOI to `CITATION.cff` (`doi:`), and the
  DOI to the paper's reproducibility section.
- Each later GitHub release becomes a new version under the same concept DOI.
