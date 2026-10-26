"""Classify every hexadecimal token in tracked files and fail on unclassified commit-like tokens in active material.

A token is 7-64 lowercase hex characters with at least one digit and one letter. Each is assigned to a class from its
provenance: dataset question IDs (from queries.json / jobs_meta.json), prompt and configuration digests, dataset and
model digests (data/MANIFEST.yaml, src/ragmv), model revisions, upload digests, third-party build logs. Anything left
over in *active publication material* (manuscript, README, guides, citation metadata, result summaries,
analysis plans) is reported as unclassified and makes the exit code 1.

Usage: python -I tools/scan_hex_refs.py [--root .] [--verbose]
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

TOKEN = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,64}(?![0-9A-Za-z])")
ACTIVE = re.compile(r"^(manuscript/.*\.(tex|bib)|README\.md|CITATION\.cff|\.zenodo\.json|LICENSE.*|docs/.*\.md|"
                    r"experiments/.*\.md|research/.*\.md|literature/.*\.md)$")
SKIP_SUFFIX = {".npz", ".png", ".pdf"}


def tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def known_classes(root: Path, files: list[str]) -> dict[str, str]:
    cls: dict[str, str] = {}

    def add(tok: str, name: str) -> None:
        cls.setdefault(tok, name)
        for n in (7, 8, 10, 12):  # abbreviated forms of the same identifier
            if len(tok) > n:
                cls.setdefault(tok[:n], name + " (abbreviated)")

    for f in files:
        p = root / f
        if f.endswith(("queries.json", "jobs_meta.json")):
            for q in json.loads(p.read_text()).get("qids", []):
                cls.setdefault(str(q).split(":", 1)[-1], "dataset question ID")
        if f.endswith("generations.jsonl"):
            for line in p.read_text().splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("prompt_sha256"):
                    cls.setdefault(row["prompt_sha256"], "prompt SHA-256")
        if f.endswith(".json"):
            for tok in re.findall(r'"config_sha256": "([0-9a-f]{64})"', p.read_text()):
                cls.setdefault(tok, "configuration SHA-256")
        if f.endswith("UPLOAD_SHA256"):
            for tok in TOKEN.findall(p.read_text()):
                cls.setdefault(tok, "upload-archive SHA-256")
    for tok in re.findall(r"sha256: ([0-9a-f]{64})", (root / "data/MANIFEST.yaml").read_text()):
        add(tok, "dataset SHA-256")
    src = "\n".join((root / "src/ragmv" / n).read_text() for n in ("dense.py", "generate.py"))
    for tok in re.findall(r'"([0-9a-f]{40})"', src):
        add(tok, "model revision (Hugging Face)")
    for tok in re.findall(r'"([0-9a-f]{64})"', src):
        add(tok, "model-file SHA-256")
    return cls


def classify(tok: str, f: str, line: str, known: dict[str, str]) -> str | None:
    if tok in known:
        return known[tok]
    if f.endswith("build_gpu.log.gz"):
        return "third-party build log"
    if "proceedings.neurips.cc" in line:
        return "publisher URL path"
    if re.search(re.escape(tok) + r"-?\d", line) and re.search(r"\d\.\d*" + re.escape(tok), line):
        return "float mantissa"
    if tok == "ed25519":
        return "ordinary word"
    if re.fullmatch(r"[0-9]+e[0-9]*", tok):
        return "float mantissa"
    if len(tok) == 64 and f.startswith("docs/remediation/"):
        return "file content SHA-256 (protected-evidence list or file inventory)"
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.root)
    files = tracked(root)
    known = known_classes(root, files)
    digest_parts = {tok[i:i + 8]: name for tok, name in known.items() if len(tok) == 64 for i in range(0, 64, 8)}
    counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    unclassified = []
    for f in files:
        p = root / f
        if p.suffix in SKIP_SUFFIX:
            continue
        for line in read_text(p).splitlines():
            for tok in TOKEN.findall(line):
                if tok.isdigit() or not re.search(r"\d", tok):
                    continue
                c = classify(tok, f, line, known) or (digest_parts.get(tok) and digest_parts[tok] + " (fragment)")
                if c is None:
                    c = "UNCLASSIFIED"
                    if ACTIVE.match(f):
                        unclassified.append((f, tok, line.strip()[:120]))
                counts[c][f] += 1
    for c in sorted(counts):
        print(f"{c}: {sum(counts[c].values())} occurrence(s) in {len(counts[c])} file(s)")
        if args.verbose:
            for f, n in sorted(counts[c].items()):
                print(f"    {f}: {n}")
    for f, tok, line in unclassified:
        print(f"UNCLASSIFIED in active material: {f}: {tok}  | {line}")
    print(f"{len(unclassified)} unclassified token(s) in active material")
    return 1 if unclassified else 0


if __name__ == "__main__":
    sys.exit(main())
