"""Check the bibliographic identity (title, authors, year, identifiers) of cited entries against authoritative records.

Sources: the Semantic Scholar graph API (DOI, arXiv and ACL Anthology identifiers), with the arXiv API as a fallback for
arXiv records. Raw responses are saved, so every judgement can be re-checked. **Identity is not content:** this tool
never changes `verification` levels (L2 = abstract read, L3 = full text read); it records an `identity_check` only.

Usage: python -I tools/verify_bib_identity.py --keys-from manuscript/main.tex --out-dir literature/identity_checks
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
S2 = "https://api.semanticscholar.org/graph/v1/paper/{}?fields=title,authors,year,venue,externalIds,publicationVenue"
S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search?query={}&limit=3&fields=title,authors,year,venue,externalIds"
ARXIV = "https://export.arxiv.org/api/query?id_list={}"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def get(url: str, tries: int = 3) -> tuple[int, str]:
    delay = 3.0
    for _ in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ragmv-bib-check"}), timeout=30) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                delay *= 2
                continue
            return e.code, e.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError) as e:
            return 0, str(e)
    return 429, "rate limited"


def identifiers(entry: dict) -> list[str]:
    raw = f"{entry.get('id') or ''} {entry.get('url') or ''}"
    out = []
    for doi in re.findall(r"(10\.\d{4,9}/[^\s;,]+)", raw):
        out.append("DOI:" + doi.rstrip("."))
    for ax in re.findall(r"(?:arXiv:|arxiv\.org/abs/)(\d{4}\.\d{4,5})", raw):
        out.append("ARXIV:" + ax)
    for acl in re.findall(r"aclanthology\.org/([A-Za-z0-9.\-]+?)/?(?:\s|$)", raw + " "):
        out.append("ACL:" + acl)
    return list(dict.fromkeys(out))


def arxiv_record(ax: str) -> dict | None:
    code, body = get(ARXIV.format(ax))
    if code != 200:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    e = ET.fromstring(body).find("a:entry", ns)
    if e is None or e.find("a:title", ns) is None:
        return None
    return {"source": "arXiv API", "title": " ".join(e.find("a:title", ns).text.split()),
            "authors": [a.find("a:name", ns).text for a in e.findall("a:author", ns)],
            "year": int(e.find("a:published", ns).text[:4]), "venue": "arXiv", "externalIds": {"ArXiv": ax}}


def judge(entry: dict, rec: dict) -> dict:
    t = difflib.SequenceMatcher(None, norm(entry["title"]), norm(rec.get("title", ""))).ratio()
    names = [a["name"] if isinstance(a, dict) else a for a in rec.get("authors") or []]
    listed = [n for n in (entry.get("authors") or []) if "et al" not in n and "(" not in n]
    first_ok = bool(names) and bool(entry.get("authors")) and norm(names[0]).split()[-1:] == \
        norm(re.sub(r"\(.*?\)|et al\.?", "", entry["authors"][0])).split()[-1:]
    year_gap = abs(int(rec.get("year") or 0) - int(entry.get("year") or 0)) if rec.get("year") else None
    return {"title_similarity": round(t, 3), "first_author_match": first_ok, "record_authors": names,
            "record_year": rec.get("year"), "year_gap": year_gap, "record_venue": rec.get("venue"),
            "record_ids": rec.get("externalIds"), "authors_in_yaml_complete": len(listed) == len(names),
            "identity_ok": t >= 0.9 and first_ok and (year_gap is not None and year_gap <= 1)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys-from", nargs="+", default=["manuscript/main.tex"])
    ap.add_argument("--bib", default="literature/bibliography.yaml")
    ap.add_argument("--out-dir", default="literature/identity_checks")
    args = ap.parse_args(argv)
    entries = {e["key"]: e for e in yaml.safe_load((ROOT / args.bib).read_text())["entries"]}
    keys = set()
    for f in args.keys_from + [str(p) for p in (ROOT / "manuscript" / "tables").glob("*.tex")]:
        for g in re.findall(r"\\cite(?:L|p|t)?\{([^}#]*)\}", (ROOT / f).read_text()):
            keys |= {k.strip() for k in g.split(",") if k.strip()}
    out_dir = ROOT / args.out_dir
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    results = {}
    for k in sorted(keys):
        e = entries[k]
        rec, src = None, None
        ax = next((p[6:] for p in identifiers(e) if p.startswith("ARXIV:")), None)
        if ax and not any(p.startswith(("DOI:", "ACL:")) for p in identifiers(e)):
            rec = arxiv_record(ax)  # the arXiv record is authoritative for arXiv-only entries
            time.sleep(3.1)
            src = f"arXiv API {ax}" if rec else None
        for pid in ([] if rec else identifiers(e)):
            code, body = get(S2.format(urllib.parse.quote(pid, safe=":/")))
            time.sleep(1.2)
            (raw_dir / f"{k}__{re.sub(r'[^A-Za-z0-9]+', '_', pid)}.json").write_text(body)
            if code == 200:
                rec, src = json.loads(body), f"Semantic Scholar {pid}"
                break
        if rec is None:
            if ax:
                rec = arxiv_record(ax)
                src = f"arXiv API {ax}" if rec else None
        if rec is None:
            code, body = get(S2_SEARCH.format(urllib.parse.quote(e["title"])))
            time.sleep(1.2)
            (raw_dir / f"{k}__search.json").write_text(body)
            if code == 200 and json.loads(body).get("data"):
                rec, src = json.loads(body)["data"][0], "Semantic Scholar title search (top hit)"
        results[k] = {"source": src, **(judge(e, rec) if rec else {"identity_ok": False, "error": "no record found"})}
        print(k, results[k].get("identity_ok"), src, flush=True)
    stamp = date.today().isoformat()
    (out_dir / f"{stamp}.json").write_text(json.dumps({"checked": stamp, "results": results}, indent=1, ensure_ascii=False))
    lines = [f"# Bibliographic identity checks ({stamp})", "",
             "Identity only (title, authors, year, identifiers) against Semantic Scholar / arXiv records; this does not "
             "verify that a cited work supports the claim it is cited for, and no verification level was changed.", "",
             "| Key | Source | Title sim. | First author | Year (record / gap) | YAML author list complete | Identity |",
             "|---|---|---:|---|---|---|---|"]
    for k, r in results.items():
        lines.append(f"| `{k}` | {r.get('source')} | {r.get('title_similarity', '—')} | {r.get('first_author_match', '—')} | "
                     f"{r.get('record_year', '—')} / {r.get('year_gap', '—')} | {r.get('authors_in_yaml_complete', '—')} | "
                     f"{'ok' if r.get('identity_ok') else 'CHECK'} |")
    (out_dir / f"{stamp}.md").write_text("\n".join(lines) + "\n")
    print(f"{sum(r.get('identity_ok', False) for r in results.values())}/{len(results)} identities ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
