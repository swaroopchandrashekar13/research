# Archiving this repository on Zenodo (DOI)

Zenodo archives a **GitHub release** and gives it a DOI. Archived files can never be changed or deleted; the record's
metadata (authors, description, licence) can be edited later. So: get the repository right first, then release.

## Before the first release
1. **Move the repository first, if you plan to, and keep its history.** A ZIP download/upload drops every commit,
   including the dated pre-registration freezes (`eb1de3c`, `20502db`). Instead, while logged in to the destination
   account, use GitHub's importer (<https://github.com/new/import>): paste
   `https://github.com/swaroopchandrashekar13/reasearch.git` as the source, choose a new repository name, set it to
   Public and start the import (full history and branches are copied). Or, with git on any computer:
   `git clone --mirror https://github.com/swaroopchandrashekar13/reasearch.git` then, inside `reasearch.git`,
   `git push --mirror https://github.com/<new-account>/<new-repo>.git` (create the empty repository first).
   Then update `repository-code` in `CITATION.cff`, enable Zenodo for the **new** repository, and keep the old one
   public and unchanged (its history is also evidence).
2. **Author:** Swaroop Chand J C (cited as "Chand J C, S."). Add your ORCID iD to `CITATION.cff` and `.zenodo.json`
   when you have one (free at <https://orcid.org>).
3. Check the metadata: `cffconvert --validate` and `python -c "import json; json.load(open('.zenodo.json'))"`.

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
