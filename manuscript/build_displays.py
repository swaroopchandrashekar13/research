"""Regenerate every manuscript display (figures, numbers.tex, tables, refs.bib) into a NEW directory, compare it
with the committed copies, and optionally promote it.

Usage:
  python -I manuscript/build_displays.py --out DIR [--compare manuscript] [--promote]

Figures are drawn by `ragmv.figures` from the validated results (dumbbells: stored shares; specification curves:
per-universe intervals with the analysis' recorded resample count and seed). SOURCE_DATE_EPOCH is fixed so PDF bytes
are reproducible. --compare reports, per file, identical / different (text files exactly; figures by their coordinate
sidecars and PDF bytes) and exits 1 on any difference. --promote copies the regenerated files into manuscript/ only
after the comparison has been printed (use it deliberately, after reviewing the differences).
"""
from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E1RUN = ROOT / "experiments/E1_retrieval_multiverse/runs/confirmatory-20261018"
E1RES = ROOT / "experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018/results.json"
E3RES = ROOT / "experiments/E3_semantic_dense/analysis/confirmatory-kaggle-gpu/results.json"
EPOCH = "1792800000"  # fixed timestamp written into regenerated PDFs (2026-10-24)


def run(cmd: list[str]) -> None:
    env = {**os.environ, "SOURCE_DATE_EPOCH": EPOCH, "PYTHONPATH": str(ROOT / "src")}
    print("$", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)


def build(out: Path) -> None:
    py = sys.executable
    raw = out / "figures_raw"
    run([py, "-I", "-c", "import sys; sys.path.insert(0, 'src'); from ragmv.figures import main; "
         f"sys.exit(main(['--run', '{E1RUN}', '--results', '{E1RES}', '--out', '{raw}', '--label', 'CONFIRMATORY']))"])
    run([py, "-I", "-c", "import sys; sys.path.insert(0, 'src'); from ragmv.figures import main; "
         f"sys.exit(main(['--study', '1b', '--results', '{E3RES}', '--out', '{raw}', '--label', 'CONFIRMATORY']))"])
    run([py, "-I", "manuscript/make_numbers.py", "--out", str(out / "numbers.tex")])
    run([py, "-I", "manuscript/make_tables.py", "--out-tables", str(out / "tables"), "--figures-from", str(raw),
         "--out-figures", str(out / "figures")])
    run([py, "-I", "manuscript/make_bib.py", "--out", str(out / "refs.bib")])


def displayed(base: Path) -> list[Path]:
    files = [Path("numbers.tex"), Path("refs.bib")]
    files += sorted(Path("tables") / p.name for p in (base / "tables").glob("*.tex"))
    files += sorted(Path("figures") / p.name for p in (base / "figures").glob("*") if p.suffix in (".pdf", ".json"))
    return files


def compare(new: Path, old: Path) -> int:
    diffs = 0
    for rel in sorted(set(displayed(new)) | set(displayed(old))):
        a, b = old / rel, new / rel
        if not a.exists() or not b.exists():
            print(f"{'only new' if b.exists() else 'only committed'}: {rel}")
            diffs += 1
        elif filecmp.cmp(a, b, shallow=False):
            print(f"identical: {rel}")
        else:
            print(f"DIFFERENT: {rel}")
            diffs += 1
    print(f"{diffs} difference(s)")
    return diffs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--compare", type=Path)
    ap.add_argument("--promote", action="store_true")
    args = ap.parse_args(argv)
    if args.out.exists() and any(args.out.iterdir()):
        raise SystemExit(f"{args.out} is not empty; regenerate into a new directory")
    build(args.out)
    n = compare(args.out, args.compare) if args.compare else 0
    if args.promote:
        dest = ROOT / "manuscript"
        for rel in displayed(args.out):
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.out / rel, dest / rel)
        print(f"promoted {len(displayed(args.out))} files into {dest}")
        return 0
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
