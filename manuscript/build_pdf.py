"""Build the named manuscript and its anonymous variant, both from main.tex, in a clean directory.

Usage: python -I manuscript/build_pdf.py --workdir DIR [--render-pages] [--report FILE]

Copies only the manuscript sources (main.tex, numbers.tex, refs.bib, tables/, figures/) into DIR and runs latexmk
(pdflatex + bibtex) twice: `main.pdf` (named) and `main-anonymous.pdf` (the same source with
\def\AnonymousSubmission{1}). Each log is classified: fatal errors (non-zero exit, `!` lines, missing files) versus
warnings (undefined references or citations, multiply defined labels, bibliography warnings, overfull and underfull
boxes, other LaTeX warnings). The anonymous PDF is checked for the author's name, PDF author metadata, repository
links and repository paths in its text and link annotations. Removing these direct identifiers does not guarantee
anonymity, and no venue's rules are checked. Exit code 1 if a build fails, any reference, citation or label problem
remains, the named PDF lacks the author, or the anonymous PDF contains an identifier. --render-pages writes one PNG
per page of each PDF (pdftoppm) for visual inspection.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = ["main.tex", "numbers.tex", "refs.bib"]
AUTHOR = "Swaroop Chand J C"
IDENTIFIERS = ("swaroop", "chand j c", "github.com", "src/ragmv", "docs/remediation", "manuscript/make_",
               "literature/bibliography")


def classify(log: str) -> dict:
    return {
        "errors": re.findall(r"^! .*", log, re.M),
        "missing_files": re.findall(r"(?:LaTeX Error: File `[^']+' not found|No file [^\s]+\.(?:tex|bbl))", log),
        "undefined_references": sorted(set(re.findall(r"Reference `([^']+)' on page \d+ undefined", log))),
        "undefined_citations": sorted(set(re.findall(r"Citation `([^']+)' on page \d+ undefined", log))),
        "multiply_defined_labels": sorted(set(re.findall(r"Label `([^']+)' multiply defined", log))),
        "overfull_boxes": re.findall(r"^Overfull \\[hv]box \(([\d.]+)pt too \w+\)", log, re.M),
        "underfull_boxes": len(re.findall(r"^Underfull \\[hv]box", log, re.M)),
        "other_latex_warnings": sorted(set(re.findall(r"LaTeX Warning: ((?!Reference|Citation|Label).*?)(?:\.|$)", log, re.M))),
        "rerun_needed": "Rerun to get cross-references right" in log or "Label(s) may have changed" in log,
    }


def build(work: Path, name: str, jobname: str | None = None, pretex: str | None = None) -> dict:
    cmd = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error"]
    if jobname:
        cmd += [f"-jobname={jobname}", f"-usepretex={pretex}"]
    proc = subprocess.run(cmd + [name], cwd=work, capture_output=True, text=True)
    stem = jobname or Path(name).stem
    log = (work / f"{stem}.log").read_text(errors="replace") if (work / f"{stem}.log").exists() else ""
    blg = (work / f"{stem}.blg").read_text(errors="replace") if (work / f"{stem}.blg").exists() else ""
    info = subprocess.run(["pdfinfo", f"{stem}.pdf"], cwd=work, capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1)) if "Pages:" in info else 0
    res = {"file": f"{stem}.pdf", "exit_code": proc.returncode, "pages": pages, **classify(log),
           "bibtex_warnings": re.findall(r"^Warning--.*", blg, re.M), "bibtex_errors": re.findall(r"error message", blg)}
    res["fatal"] = bool(proc.returncode or res["errors"] or res["missing_files"] or not pages)
    res["reference_problems"] = bool(res["undefined_references"] or res["undefined_citations"]
                                     or res["multiply_defined_labels"] or res["rerun_needed"])
    return res


def identity_check(work: Path, stem: str) -> dict:
    """Author and repository identifiers in a PDF's metadata, text and link annotations."""
    info = subprocess.run(["pdfinfo", f"{stem}.pdf"], cwd=work, capture_output=True, text=True).stdout
    author = (re.search(r"^Author:[ \t]*(.*)$", info, re.M) or [None, ""])[1].strip()
    text = subprocess.run(["pdftotext", "-layout", f"{stem}.pdf", "-"], cwd=work, capture_output=True, text=True).stdout
    data = (work / f"{stem}.pdf").read_bytes()
    parts = [data]
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):  # object streams hold the link annotations
        try:
            parts.append(zlib.decompress(m.group(1)))
        except zlib.error:
            pass
    raw = b"\n".join(parts).decode("latin-1")
    uris = sorted(set(re.findall(r"/URI\s*\(([^)]*)\)", raw)))
    flat = " ".join(text.lower().split())
    return {"pdf_author": author, "author_in_text": AUTHOR.lower() in flat,
            "identifiers_in_text": [i for i in IDENTIFIERS if i in flat],
            "identifying_links": [u for u in uris if any(i in u.lower() for i in IDENTIFIERS)], "links": len(uris)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True, type=Path)
    ap.add_argument("--render-pages", action="store_true")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    work = args.workdir
    if work.exists() and any(work.iterdir()):
        raise SystemExit(f"{work} is not empty; build in a clean directory")
    work.mkdir(parents=True, exist_ok=True)
    for f in SOURCES:
        shutil.copy2(HERE / f, work / f)
    for d in ("tables", "figures"):
        shutil.copytree(HERE / d, work / d)
    named = build(work, "main.tex")
    anon = build(work, "main.tex", "main-anonymous", r"\def\AnonymousSubmission{1}")
    results = [named, anon]
    if not named["fatal"]:
        named["identity"] = identity_check(work, "main")
        named["identity_ok"] = named["identity"]["pdf_author"] == AUTHOR and named["identity"]["author_in_text"]
    if not anon["fatal"]:
        anon["identity"] = identity_check(work, "main-anonymous")
        i = anon["identity"]
        anon["identity_ok"] = not (i["pdf_author"] or i["author_in_text"] or i["identifiers_in_text"] or i["identifying_links"])
    if args.render_pages:
        for stem in ("main", "main-anonymous"):
            (work / "pages" / stem).mkdir(parents=True)
            subprocess.run(["pdftoppm", "-r", "60", "-png", f"{stem}.pdf", f"pages/{stem}/page"], cwd=work, check=True)
    summary = json.dumps(results, indent=1)
    if args.report:
        args.report.write_text(summary)
    print(summary)
    return 1 if any(r["fatal"] or r["reference_problems"] or not r.get("identity_ok") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
