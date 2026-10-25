"""Remove machine-readable hashes from the HISTORICAL evidence files (second redaction pass, 2026-10-25).

Scope (owner's decision): the original run directories and original analysis outputs under experiments/ —
run manifests, results.json/results.md, generations.jsonl, jobs_meta.json, UPLOAD_SHA256 and build_gpu.log.gz.
Out of scope and kept: dataset question IDs (they are data, not hashes); checksums that code and tools use for
verification (data/MANIFEST.yaml, model pins in src/ragmv, docs/repair/PROTECTED_SHA256.txt); the post-hoc
analyses of 2026-10-24 (new work) and anything written by new runs.

Each hash value is replaced by a fixed marker; JSON/JSONL are edited as text, so every other byte is unchanged.
The gzip build log is decompressed, edited the same way and recompressed deterministically (mtime 0). The tool
stores no hash values itself.

Usage: python -I tools/redact_historical_hashes.py --check | --apply   (exit 1 from --check if anything remains)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIST = re.compile(r"^experiments/[^/]+/(runs/.*|analysis/(confirmatory|pilot|exploratory|qwen3)[^/]*/.*)$")
DIGEST = "redacted: historical digest removed"
REV = "[revision removed]"
TOKEN = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,64}(?![0-9A-Za-z])")

RULES = [  # (pattern, replacement) applied to JSON / JSONL / Markdown text
    (re.compile(r'("(?:config_sha256|prompt_sha256)": ")[0-9a-f]{64}(")'), r"\g<1>" + DIGEST + r"\g<2>"),
    (re.compile(r"(@)[0-9a-f]{8,40}(?=[/|`\"'\s])"), r"\g<1>" + REV),  # model@revision inside model/encoder strings
    (re.compile(r'^(\s*)"[0-9a-f]{40}"(,?)$', re.M), r'\g<1>"redacted: model revision removed"\g<2>'),  # jobs_meta lists
    (re.compile(r'^(\s*)"[0-9a-f]{64}"(,?)$', re.M), r'\g<1>"redacted: model file digest removed"\g<2>'),
]


def historical_files() -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True, check=True).stdout
    return [f for f in out.split() if HIST.match(f)]


def qids(files: list[str]) -> set[str]:
    s = set()
    for f in files:
        if f.endswith(("queries.json", "jobs_meta.json")):
            s |= {str(q).split(":", 1)[-1] for q in json.loads((ROOT / f).read_text()).get("qids", [])}
    return s


def redact_text(text: str) -> tuple[str, int]:
    n = 0
    for pat, rep in RULES:
        text, k = pat.subn(rep, text)
        n += k
    return text, n


def redact_log(text: str, keep: set[str]) -> tuple[str, int]:
    count = 0

    def sub(m):
        nonlocal count
        t = m.group(0)
        if t.isdigit() or not re.search(r"\d", t) or t in keep:
            return t
        count += 1
        return "[hash removed]"
    return TOKEN.sub(sub, text), count


def remaining(text: str, keep: set[str]) -> list[str]:
    out = []
    for m in TOKEN.finditer(text):
        t = m.group(0)
        if t.isdigit() or not re.search(r"\d", t) or t in keep:
            continue
        line = text[max(0, m.start() - 20): m.end() + 2]
        if re.search(r"\d\.\d*" + re.escape(t) + r"-?\d", line) or re.fullmatch(r"[0-9]+e[0-9]*", t):
            continue  # float mantissa such as 1.0864...e-05
        out.append(t)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    files = historical_files()
    keep = qids(files)
    left = pending = 0
    for f in files:
        p = ROOT / f
        if p.suffix in (".npz", ".png", ".pdf"):
            continue
        raw = p.read_bytes()
        if p.name == "UPLOAD_SHA256":
            text = raw.decode()
            new = "redacted: upload-archive digest removed 2026-10-25 (docs/repair/HASH_REDACTIONS.md)\n"
            n = 1 if re.search(r"[0-9a-f]{64}", text) else 0
            out = new.encode() if n else raw
        elif p.suffix == ".gz":
            text = gzip.decompress(raw).decode("utf-8", "replace")
            if f.endswith(".log.gz"):
                new, n = redact_log(text, keep)
                out = gzip.compress(new.encode(), mtime=0) if n else raw
            else:
                new, n, out = text, 0, raw
        else:
            text = raw.decode("utf-8")
            new, n = redact_text(text)
            out = new.encode() if n else raw
        rest = remaining(new, keep)
        left += len(rest)
        pending += n
        if args.apply and n:
            p.write_bytes(out)
            print(f"{f}\t{n}\tpre={hashlib.sha256(raw).hexdigest()}\tpost={hashlib.sha256(out).hexdigest()}")
        elif args.check and (n or rest):
            print(f"{f}\t{n} redactable, {len(rest)} other hash-like token(s)")
    print(f"{left} hash-like token(s) other than dataset question IDs remain after redaction rules", file=sys.stderr)
    if args.check:
        print(f"{pending} redactable hash value(s) pending", file=sys.stderr)
        return 1 if (left or pending) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
