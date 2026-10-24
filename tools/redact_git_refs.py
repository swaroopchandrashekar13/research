"""Redact unresolvable historical Git commit identifiers from JSON run metadata, in place and byte-minimally.

The project's original version-control history is no longer available, so the commit identifiers that historical
run manifests, generation metadata and analysis results recorded in their `"git"` fields cannot be resolved by anyone.
This tool replaces only the value of each `"git": "<40 hex>[-dirty]"` field with a fixed marker; every other byte of
the file is left untouched (the JSON is edited as text, never re-serialised). The `-dirty` flag is kept because it is
working-tree state, not a commit identifier. Content digests (dataset, config, prompt, model, archive) are never
touched. The tool stores no identifiers itself: it matches the field pattern.

Usage:
  python -I tools/redact_git_refs.py --check  [paths...]   # list files that still contain a commit-valued "git" field
  python -I tools/redact_git_refs.py --apply  [paths...]   # redact them; prints file, count, pre/post SHA-256
Default paths: experiments/
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

GIT_FIELD = re.compile(r'("git": ")([0-9a-f]{40})(-dirty)?(")')
MARKER = "redacted: unresolvable historical Git commit"
MARKER_DIRTY = MARKER + " (working tree was dirty)"


def _replace(m: re.Match) -> str:
    return m.group(1) + (MARKER_DIRTY if m.group(3) else MARKER) + m.group(4)


def redact_text(text: str) -> tuple[str, int]:
    return GIT_FIELD.subn(_replace, text)


def iter_json(paths: list[Path]):
    for p in paths:
        if p.is_dir():
            yield from sorted(q for q in p.rglob("*.json") if q.is_file())
        elif p.suffix == ".json":
            yield p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    ap.add_argument("paths", nargs="*", default=["experiments"])
    args = ap.parse_args(argv)
    remaining = 0
    for path in iter_json([Path(p) for p in args.paths]):
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        new, n = redact_text(text)
        if not n:
            continue
        remaining += n
        if args.apply:
            out = new.encode("utf-8")
            path.write_bytes(out)
            print(f"{path}\t{n}\tpre={hashlib.sha256(raw).hexdigest()}\tpost={hashlib.sha256(out).hexdigest()}")
        else:
            print(f"{path}\t{n} commit-valued git field(s)")
    if args.check:
        print(f"{remaining} commit-valued git field(s) found")
        return 1 if remaining else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
