"""Read-only check of the hash policy for stored evidence (it never modifies a file).

Owner decision: machine-readable identities (configuration and prompt digests, model revisions, model-file and
upload-archive digests, build-log identifiers) stay removed from the original runs and original analysis outputs;
they are not recovered. The policy, as `ragmv.provenance` implements it for the validators:

1. Historical evidence (original run directories and original analysis outputs) contains no hash value other than
   dataset question IDs; every removed value is one of the exact markers.
2. Removed-value markers occur only in the registered historical runs (`ragmv.provenance.HISTORICAL_RUNS`), in the
   analysis outputs derived from them, and in the three registered upload files.
3. The model identities that new runs use are pinned in code (`ragmv.dense`, `ragmv.generate`), so new runs record
   real values; the validators reject markers anywhere else.

Usage: python -I tools/check_hash_policy.py      (exit 1 on any violation)
"""
from __future__ import annotations

import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ragmv import provenance as PV  # noqa: E402

HIST = re.compile(r"^experiments/[^/]+/(runs/.*|analysis/(confirmatory|pilot|exploratory|qwen3)[^/]*/.*)$")
TOKEN = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,64}(?![0-9A-Za-z])")
MARKERS = (PV.DIGEST_REMOVED, PV.REVISION_REMOVED, PV.MODEL_REVISION_REMOVED, PV.MODEL_FILE_DIGEST_REMOVED,
           PV.UPLOAD_REMOVED, "[hash removed]")


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout
    return [f for f in out.splitlines() if f]


def text_of(path: Path) -> str | None:
    if path.suffix in (".npz", ".png", ".pdf"):
        return None
    raw = path.read_bytes()
    if path.suffix == ".gz":
        raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def question_ids(files: list[str]) -> set[str]:
    out = set()
    for f in files:
        if f.endswith(("queries.json", "jobs_meta.json")):
            out |= {str(q).split(":", 1)[-1] for q in json.loads((ROOT / f).read_text()).get("qids", [])}
    return out


def hash_like(text: str, keep: set[str]) -> list[str]:
    found = []
    for m in TOKEN.finditer(text):
        t = m.group(0)
        if t.isdigit() or not re.search(r"\d", t) or t in keep:
            continue
        ctx = text[max(0, m.start() - 20): m.end() + 2]
        if re.search(r"\d\.\d*" + re.escape(t) + r"-?\d", ctx) or re.fullmatch(r"[0-9]+e[0-9]*", t):
            continue  # float mantissa such as 1.0864...e-05
        found.append(t)
    return found


def marker_allowed(f: str) -> bool:
    if f in PV.UPLOAD_FILES or f == "docs/remediation/HASH_POLICY.md":  # the policy document names the markers
        return True
    if any(f.startswith(run + "/") for run in PV.HISTORICAL_RUNS):
        return True
    return bool(HIST.match(f)) and "/analysis/" in f  # analysis outputs that copy the historical manifests' fields


def main() -> int:
    files = tracked()
    hist = [f for f in files if HIST.match(f)]
    keep = question_ids(hist)
    problems = []
    for f in hist:
        text = text_of(ROOT / f)
        if text is None:
            continue
        left = hash_like(text, keep)
        if left:
            problems.append(f"{f}: {len(left)} hash-like value(s) in historical evidence")
    for f in files:
        if f.startswith(("src/", "tools/", "tests/")):
            continue  # the policy constants and their tests name the markers
        text = text_of(ROOT / f)
        if text and any(m in text for m in MARKERS) and not marker_allowed(f):
            problems.append(f"{f}: removed-value marker outside the registered historical records")
    from ragmv import dense, generate
    if not PV.is_hex_digest(dense.REVISION, 40):
        problems.append("ragmv.dense.REVISION is not a full model revision")
    for name, (_, rev, _, sha, _) in generate.LOCAL_MODELS.items():
        if not (PV.is_hex_digest(rev, 40) and PV.is_hex_digest(sha)):
            problems.append(f"ragmv.generate.LOCAL_MODELS[{name!r}] lacks a full revision or file digest")
    for p in problems:
        print(f"VIOLATION: {p}")
    print(f"{len(hist)} historical evidence files checked; {len(problems)} violation(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
