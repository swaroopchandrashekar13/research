"""Check that CITATION.cff and .zenodo.json are well-formed and agree, and optionally record the author's ORCID iD.

  python -I tools/check_release_metadata.py                      # check; exit 1 on any failure
  python -I tools/check_release_metadata.py --set-orcid <your ORCID iD, e.g. 0000-000X-XXXX-XXXX>

Checks: required CFF fields; the same title, authors (in the same order) and keywords in both files; licences that
match LICENSE and LICENSE-DATA.md; no repository-hosting URL (the repository may move); no placeholder values;
ORCID iDs and DOIs, when present, in the right form (an ORCID iD's last character is its ISO 7064 MOD 11-2 check
digit). A missing ORCID iD or DOI is reported as a note: neither is required, and neither is ever filled in for you.
--set-orcid writes an iD that passes the check into both files (first author) and changes nothing else.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CFF, ZEN = ROOT / "CITATION.cff", ROOT / ".zenodo.json"
ORCID = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]")
DOI = re.compile(r"10\.\d{4,9}/\S+")
HOSTING = re.compile(r"https?://(?:www\.)?(?:github\.com|gitlab\.com|bitbucket\.org|codeberg\.org)/", re.I)
PLACEHOLDER = re.compile(r"\b(?:TODO|TBD|FIXME|XXXX|0000-0000-0000-0000|your[- ]name|example\.com)\b", re.I)


def orcid_ok(value: str) -> bool:
    """ISO 7064 MOD 11-2 check digit of the 15 preceding digits."""
    if not ORCID.fullmatch(value):
        return False
    digits = value.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    check = (12 - total % 11) % 11
    return digits[-1] == ("X" if check == 10 else str(check))


def check(cff: dict, zen: dict, cff_text: str, zen_text: str) -> tuple[list[str], list[str]]:
    fail, notes = [], []
    for k in ("cff-version", "message", "title", "authors"):
        if not cff.get(k):
            fail.append(f"CITATION.cff: missing {k}")
    if cff.get("cff-version") != "1.2.0":
        fail.append(f"CITATION.cff: cff-version {cff.get('cff-version')!r} (expected 1.2.0)")
    for k in ("title", "upload_type", "creators", "description", "license"):
        if not zen.get(k):
            fail.append(f".zenodo.json: missing {k}")
    if cff.get("title") != zen.get("title"):
        fail.append("title differs between CITATION.cff and .zenodo.json")
    cff_names = [f"{a.get('family-names', '')}, {a.get('given-names', '')}" for a in cff.get("authors") or []]
    zen_names = [c.get("name") for c in zen.get("creators") or []]
    if cff_names != zen_names:
        fail.append(f"authors differ: {cff_names} vs {zen_names}")
    if sorted(cff.get("keywords") or []) != sorted(zen.get("keywords") or []):
        fail.append("keywords differ between CITATION.cff and .zenodo.json")
    if sorted(cff.get("license") or []) != ["CC-BY-4.0", "MIT"]:
        fail.append(f"CITATION.cff licence {cff.get('license')} does not match LICENSE (MIT) and LICENSE-DATA.md (CC BY 4.0)")
    if "MIT License" not in (ROOT / "LICENSE").read_text() or "CC BY 4.0" not in (ROOT / "LICENSE-DATA.md").read_text():
        fail.append("LICENSE or LICENSE-DATA.md does not state the licences named in the metadata")
    for name, text in (("CITATION.cff", cff_text), (".zenodo.json", zen_text)):
        if HOSTING.search(text):
            fail.append(f"{name}: names a repository-hosting URL")
        if PLACEHOLDER.search(text):
            fail.append(f"{name}: contains a placeholder value")
    for a in cff.get("authors") or []:
        o = a.get("orcid")
        if o is None:
            notes.append(f"ORCID iD not set for {a.get('given-names')} {a.get('family-names')} (optional; "
                         "add it with --set-orcid when you have one)")
        elif not (o.startswith("https://orcid.org/") and orcid_ok(o.rsplit("/", 1)[-1])):
            fail.append(f"CITATION.cff: ORCID {o!r} is not https://orcid.org/ followed by a valid iD")
    for c, a in zip(zen.get("creators") or [], cff.get("authors") or []):
        o = c.get("orcid")
        if o is not None and not orcid_ok(o):
            fail.append(f".zenodo.json: ORCID {o!r} is not a valid iD")
        if (o or None) != ((a.get("orcid") or "").rsplit("/", 1)[-1] or None):
            fail.append("ORCID iDs differ between CITATION.cff and .zenodo.json")
    doi = cff.get("doi")
    if doi is None:
        notes.append("DOI not set (the archive assigns it on publication; add it afterwards)")
    elif not DOI.fullmatch(str(doi)):
        fail.append(f"CITATION.cff: DOI {doi!r} is not of the form 10.NNNN/suffix")
    return fail, notes


def set_orcid(value: str) -> None:
    if not orcid_ok(value):
        raise SystemExit(f"{value!r} is not a valid ORCID iD (form 0000-0000-0000-000X with a correct check digit)")
    text = CFF.read_text()
    if re.search(r"^\s+orcid:", text, re.M):
        text = re.sub(r'^(\s+orcid:\s*).*$', rf'\g<1>"https://orcid.org/{value}"', text, count=1, flags=re.M)
    else:
        text, n = re.subn(r'^(\s+given-names:.*\n)', rf'\g<1>    orcid: "https://orcid.org/{value}"\n', text,
                          count=1, flags=re.M)
        if n != 1:
            raise SystemExit("CITATION.cff: no author entry to add the iD to")
    zen = json.loads(ZEN.read_text())
    zen["creators"][0]["orcid"] = value
    CFF.write_text(text)
    ZEN.write_text(json.dumps(zen, indent=2, ensure_ascii=False) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--set-orcid", metavar="ID")
    args = ap.parse_args(argv)
    if args.set_orcid:
        set_orcid(args.set_orcid)
    cff_text, zen_text = CFF.read_text(), ZEN.read_text()
    fail, notes = check(yaml.safe_load(cff_text), json.loads(zen_text), cff_text, zen_text)
    for x in fail:
        print(f"FAIL  {x}")
    for x in notes:
        print(f"NOTE  {x}")
    print(f"{len(fail)} failure(s), {len(notes)} note(s)")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
