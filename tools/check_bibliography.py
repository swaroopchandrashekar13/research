"""Validate literature/bibliography.yaml and refuse citations below a minimum verification level.

Usage:
  python tools/check_bibliography.py                    # validate schema
  python tools/check_bibliography.py --cite KEY [KEY..] --min-level L2   # gate citations in a manuscript
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ("L0", "L1", "L2", "L3")
REQUIRED = ("key", "title", "year", "venue", "verification", "directions")


def load(path: str | Path) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text())
    return data["entries"]


def validate(entries: list[dict]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            errors.append(f"entry #{i}: not a mapping")
            continue
        where = e.get("key", f"entry #{i}")
        for field in REQUIRED:
            if e.get(field) in (None, "", []):
                errors.append(f"{where}: missing required field '{field}'")
        if e.get("key") in seen:
            errors.append(f"{where}: duplicate key")
        seen.add(e.get("key"))
        if e.get("verification") not in LEVELS:
            errors.append(f"{where}: verification must be one of {LEVELS}")
        if e.get("verification") == "L0":
            errors.append(f"{where}: L0 entries must not be stored; verify or delete")
        if not (e.get("url") or e.get("id")):
            errors.append(f"{where}: needs at least a url or an id")
    return errors


def citable(entries: list[dict], keys: list[str], min_level: str) -> list[str]:
    """Return problems preventing `keys` from being cited at `min_level` or above."""
    by_key = {e["key"]: e for e in entries}
    floor = LEVELS.index(min_level)
    problems = []
    for k in keys:
        if k not in by_key:
            problems.append(f"{k}: not in bibliography")
        elif LEVELS.index(by_key[k]["verification"]) < floor:
            problems.append(f"{k}: verified only to {by_key[k]['verification']} (< {min_level})")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bib", default=str(ROOT / "literature" / "bibliography.yaml"))
    ap.add_argument("--cite", nargs="*", default=[])
    ap.add_argument("--min-level", default="L2", choices=LEVELS)
    args = ap.parse_args()
    entries = load(args.bib)
    problems = validate(entries) + citable(entries, args.cite, args.min_level)
    for p in problems:
        print("ERROR", p)
    counts = {lvl: sum(e.get("verification") == lvl for e in entries) for lvl in LEVELS}
    print(f"{len(entries)} entries; by level: {counts}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
