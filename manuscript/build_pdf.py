"""Build the canonical manuscript (and its anonymous variant) with bibliography in a clean directory.

Usage: python -I manuscript/build_pdf.py --workdir DIR [--render-pages] [--report FILE]

Copies only the manuscript sources (main.tex, main_anonymous.tex, numbers.tex, refs.bib, tables/, figures/) into
DIR, runs latexmk (pdflatex + bibtex) and classifies the log: fatal errors (non-zero exit, `!` lines, missing files)
versus warnings (undefined references or citations, multiply defined labels, overfull boxes, other LaTeX warnings).
Exit code 1 if the build fails or any reference, citation or label problem remains. --render-pages writes one PNG per
page (pdftoppm) for visual inspection.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES = ["main.tex", "main_anonymous.tex", "numbers.tex", "refs.bib"]


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


def build(work: Path, name: str) -> dict:
    proc = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", name],
                          cwd=work, capture_output=True, text=True)
    stem = Path(name).stem
    log = (work / f"{stem}.log").read_text(errors="replace") if (work / f"{stem}.log").exists() else ""
    blg = (work / f"{stem}.blg").read_text(errors="replace") if (work / f"{stem}.blg").exists() else ""
    info = subprocess.run(["pdfinfo", f"{stem}.pdf"], cwd=work, capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1)) if "Pages:" in info else 0
    res = {"file": name, "exit_code": proc.returncode, "pages": pages, **classify(log),
           "bibtex_warnings": re.findall(r"^Warning--.*", blg, re.M), "bibtex_errors": re.findall(r"error message", blg)}
    res["fatal"] = bool(proc.returncode or res["errors"] or res["missing_files"] or not pages)
    res["reference_problems"] = bool(res["undefined_references"] or res["undefined_citations"]
                                     or res["multiply_defined_labels"] or res["rerun_needed"])
    return res


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
    results = [build(work, "main.tex"), build(work, "main_anonymous.tex")]
    if args.render_pages:
        (work / "pages").mkdir()
        subprocess.run(["pdftoppm", "-r", "60", "-png", "main.pdf", "pages/page"], cwd=work, check=True)
    summary = json.dumps(results, indent=1)
    if args.report:
        args.report.write_text(summary)
    print(summary)
    return 1 if any(r["fatal"] or r["reference_problems"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
