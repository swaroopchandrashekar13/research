"""Generate refs.bib from literature/bibliography.yaml for every key cited in the manuscript .tex files.

Usage: python -I manuscript/make_bib.py [--tex-dir manuscript] [--bib-yaml literature/bibliography.yaml] [--out refs.bib]
Only verified entries (L1+) exist in bibliography.yaml, so nothing from memory can enter the paper. The verification
level of each entry is kept in bibliography.yaml (and gated by tools/check_bibliography.py --min-level); the run prints
how many cited entries are below L3. Keys are collected from the canonical manuscript (main.tex and the files it
inputs) and the generated tables.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "manuscript"


def cited_keys(tex_dir: Path = HERE) -> list[str]:
    keys: list[str] = []
    for tex in sorted(tex_dir.glob("*.tex")) + sorted((tex_dir / "tables").glob("*.tex")):
        for group in re.findall(r"\\cite(?:L|p|t)?\{([^}#]*)\}", tex.read_text()):
            keys += [k.strip() for k in group.split(",") if k.strip() and k.strip() != "key"]
    return sorted(set(keys))


def authors(e: dict) -> str:
    """BibTeX author list. `bibtex_authors` (\"Last, First\" form) overrides `authors` where the surname has several
    parts or starts with an accented letter; hyphenated given names are braced so that they print unchanged."""
    if e.get("bibtex_authors"):
        return " and ".join(e["bibtex_authors"])
    names = e.get("authors") or []
    if not names:
        return "{[authors not yet verified]}"
    out = []
    for n in names:
        n = re.sub(r"\s*\(.*?\)", "", n).strip()
        if n.endswith("et al."):
            out += [n[: -len("et al.")].strip(), "others"]
            continue
        parts = n.split()
        out.append(" ".join([f"{{{t}}}" if "-" in t else t for t in parts[:-1]] + parts[-1:]))
    return " and ".join(out)


VOLUME = re.compile(r"^(?P<name>.*?)\s+(?P<vol>\d+)\((?P<num>\d+)\):(?P<p1>\d+)-(?P<p2>\d+)$")
PAGES = re.compile(r"^(?P<name>.*?),\s*pp\.\s*(?P<p1>\d+)-(?P<p2>\d+)$")


def venue_fields(venue: str, year) -> dict:
    """Split "Journal 4(11):1208-1214" and "Proceedings, pp. 1-9" into name, volume, number and pages; drop a
    trailing year that repeats the entry's year."""
    out = {}
    m = VOLUME.match(venue) or PAGES.match(venue)
    if m:
        venue = m["name"]
        out["pages"] = f"{m['p1']}--{m['p2']}"
        if "vol" in m.groupdict():
            out["volume"], out["number"] = m["vol"], m["num"]
    venue = re.sub(rf"\s+{year}$", "", venue)
    out["name"] = venue
    return out


def esc(s: str) -> str:
    return s.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def entry(e: dict) -> str:
    venue = str(e["venue"])
    fields = {"author": authors(e), "title": "{" + esc(e["title"]) + "}", "year": str(e["year"])}
    ids = [x for x in str(e.get("id") or "").split("; ") if x]
    doi = e.get("doi") or next((x[4:] for x in ids if x.startswith("doi:")), None)
    if venue.lower().startswith("arxiv"):
        kind = "misc"
        arxiv = next((x for x in ids if x.lower().startswith("arxiv:")), None)
        fields["howpublished"] = esc(f"arXiv preprint {arxiv}" if arxiv else "arXiv preprint")
    else:
        kind = "inproceedings" if any(w in venue for w in ("Findings", "ACL", "EMNLP", "NeurIPS", "CIKM", "SIGIR",
                                                          "NAACL")) else "article"
        v = venue_fields(venue, e["year"])
        fields["booktitle" if kind == "inproceedings" else "journal"] = esc(v["name"])
        for k in ("volume", "number", "pages"):
            if k in v:
                fields[k] = v[k]
        # the DOI and the URL are printed from their own fields; an Anthology ID repeats the Anthology URL
        url = str(e.get("url") or "")
        rest = [x for x in ids if not x.startswith("doi:") and not x.startswith("ACL Anthology") and x not in url]
        if rest:
            fields["note"] = esc("; ".join(rest))
    if e.get("pages") and kind != "misc" and "pages" not in fields:
        fields["pages"] = str(e["pages"]).replace("-", "--")
    if doi:
        fields["doi"] = doi
    if e.get("url") and not (doi and "doi.org/" in e["url"]):
        fields["url"] = e["url"]
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items())
    return f"@{kind}{{{e['key']},\n{body}\n}}\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tex-dir", type=Path, default=HERE)
    ap.add_argument("--bib-yaml", type=Path, default=ROOT / "literature/bibliography.yaml")
    ap.add_argument("--out", type=Path, default=HERE / "refs.bib")
    args = ap.parse_args(argv)
    entries = {e["key"]: e for e in yaml.safe_load(args.bib_yaml.read_text())["entries"]}
    keys = cited_keys(args.tex_dir)
    missing = [k for k in keys if k not in entries]
    if missing:
        raise SystemExit(f"cited but not in bibliography.yaml (verify first, never cite from memory): {missing}")
    text = "% Generated by manuscript/make_bib.py from literature/bibliography.yaml. Do not edit by hand.\n\n"
    text += "\n".join(entry(entries[k]) for k in keys)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text)
    below = [k for k in keys if entries[k]["verification"] != "L3"]
    print(f"{len(keys)} entries written; {len(below)} below verification level L3 (see literature/bibliography.yaml)")


if __name__ == "__main__":
    main()
