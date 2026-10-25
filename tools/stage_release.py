"""Build and verify the metrics-only release package (a zip for an archive deposit). Nothing in the repository is
changed, nothing is uploaded.

  build   python -I tools/stage_release.py build --out DIR/ragmv-release.zip [--allow-dirty]
  verify  python -I tools/stage_release.py verify DIR/ragmv-release.zip [--source .] [--data-root data/raw]
                 [--recompute] [--report FILE]

Build reads the files Git tracks (a clean working tree is required unless --allow-dirty, which also takes untracked,
not-ignored files) and gives every file exactly one rule from RULES; a file no rule names stops the build, so a new
file is released only after someone has decided what it is. Generation logs are converted to their metrics-only form
(`ragmv.metrics_form`: explicit field allowlist, answer and response strings removed). The protected-digest list
keeps the lines of files that are in the package. `release/` supplies the package's own LICENSE-DATA.md and
PACKAGE.md. A SHA256SUMS file lists every other file of the package. The zip is deterministic (sorted entries,
fixed timestamps and permissions) and holds no Git history, caches or credentials.

Verify reads the zip itself: entry paths, SHA256SUMS, the rule of every entry, the schema of every metrics file,
forbidden JSON keys, private paths and credential patterns, and that no answer or response string of the source
logs (at least MIN_LEAK_CHARS characters) occurs anywhere in it. With --data-root it also looks for any run of
SHINGLE words copied from the datasets' documents or questions (dataset question IDs are removed first). With
--recompute it extracts the package and, using only the package's own code and files, reruns the structural
validation, the test suite, the E1, E3 and E2 analyses and the independent statistical checks, compares every
scientific field with the package's stored results, and checks the files each analysis read against SHA256SUMS.
"""
from __future__ import annotations

import argparse
import fnmatch
import gzip
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ragmv import metrics_form as MF  # noqa: E402

TOP = "ragmv-release"
SUMS = "SHA256SUMS"
PROTECTED = "docs/remediation/PROTECTED_SHA256.txt"
EPOCH = (1980, 1, 1, 0, 0, 0)
MAX_ENTRY_BYTES = 5_000_000
MIN_LEAK_CHARS = 25
SHINGLE = 8
GEN_LOG = "experiments/E2_generation/runs/*/*/generations*.jsonl"

PACKAGE_FILES = ("LICENSE-DATA.md", "PACKAGE.md")  # release/<name> becomes <name> at the package root
QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"')

# (pattern, action); fnmatch patterns ("*" also matches "/"). First match wins. Actions: copy | metrics (generation log -> metrics-only form) | protected
# (digest lines of files not in the package are left out) | package (taken from release/) | exclude.
RULES = [
    (GEN_LOG, "metrics"),
    (PROTECTED, "protected"),
    ("release/*", "package"),
    # Semantic Scholar API responses: the API licence could not be read from the checking environment (unresolved).
    ("literature/identity_checks/raw/*.json", "exclude"),
    ("LICENSE-DATA.md", "exclude"),  # replaced by release/LICENSE-DATA.md
    ("literature/identity_checks/raw/*.bib", "copy"),  # ACL Anthology records (CC BY 4.0 for 2016 onwards)
    ("literature/identity_checks/*", "copy"),
    ("literature/protocol_audit/*", "copy"),
    ("literature/*.md", "copy"), ("literature/*.yaml", "copy"),
    ("src/ragmv/*.py", "copy"), ("tests/*.py", "copy"), ("tools/*.py", "copy"),
    ("manuscript/*.py", "copy"), ("manuscript/*.tex", "copy"), ("manuscript/*.bib", "copy"),
    ("manuscript/tables/*.tex", "copy"), ("manuscript/figures/*", "copy"),
    ("experiments/*.md", "copy"), ("experiments/*/*.md", "copy"), ("experiments/*/*.py", "copy"),
    ("experiments/*/*.sh", "copy"),
    ("experiments/*/runs/*", "copy"), ("experiments/*/analysis/*", "copy"),
    ("research/*.md", "copy"), ("docs/remediation/*", "copy"), ("docs/guides/*.md", "copy"),
    ("data/MANIFEST.yaml", "copy"), ("env/environment.json", "copy"), ("env/validation/*", "copy"),
    ("requirements/*.txt", "copy"), ("requirements/README.md", "copy"), ("manuscript/matplotlibrc", "copy"), ("requirements.txt", "copy"), ("requirements-study1b.txt", "copy"),
    ("pyproject.toml", "copy"), ("README.md", "copy"), ("LICENSE", "copy"), ("CITATION.cff", "copy"),
    (".zenodo.json", "copy"), (".gitignore", "copy"), (".github/workflows/*.yml", "copy"),
]
FORBIDDEN_KEYS = {"answers", "answer", "response", "prompt", "question", "context", "passage", "passages",
                  "completion", "output", "gold_text"}
FORBIDDEN_PARTS = {".git", "__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".venv", "venv", ".DS_Store"}
PRIVATE_PATH = re.compile(r"(/home/[A-Za-z0-9_.-]+/|/Users/[A-Za-z0-9_.-]+/|/data/data/com\.termux/|"
                          r"[A-Za-z]:\\Users\\|/tmp/clau[d]e)")
CREDENTIAL = re.compile(r"(AIza[0-9A-Za-z_\-]{35}|sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}|"
                        r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY)")
TOKEN = re.compile(r"[a-z0-9]+")


class StageError(RuntimeError):
    pass


def rule_for(rel: str) -> str | None:
    return next((action for pattern, action in RULES if fnmatch.fnmatchcase(rel, pattern)), None)


def _git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def source_files(root: Path = ROOT, allow_dirty: bool = False) -> list[str]:
    if not (root / ".git").exists():
        raise StageError("build needs a Git checkout (the file list is what Git tracks)")
    if not allow_dirty and _git("status", "--porcelain", root=root).strip():
        raise StageError("the working tree has uncommitted changes; commit them or pass --allow-dirty")
    args = ["ls-files", "-z"] + (["--cached", "--others", "--exclude-standard"] if allow_dirty else [])
    return sorted({f for f in _git(*args, root=root).split("\0") if f and (root / f).is_file()})


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def plan(root: Path = ROOT, allow_dirty: bool = False) -> dict[str, bytes]:
    """Published path -> content of every file of the package (without SHA256SUMS)."""
    files = source_files(root, allow_dirty)
    unruled = [f for f in files if rule_for(f) is None]
    if unruled:
        raise StageError(f"{len(unruled)} file(s) have no release rule (review them, then add a rule): {unruled[:10]}")
    out: dict[str, bytes] = {}
    for f in files:
        action = rule_for(f)
        if action == "copy":
            out[f] = (root / f).read_bytes()
        elif action == "metrics":
            p = Path(f)
            out[str(p.with_name(MF.metrics_name(p.name)))] = MF.convert_log(root / f).encode("utf-8")
        elif action == "package":
            if Path(f).name not in PACKAGE_FILES:
                raise StageError(f"{f}: release/ may hold only {PACKAGE_FILES}")
            out[Path(f).name] = (root / f).read_bytes()
    missing = [n for n in PACKAGE_FILES if n not in out]
    if missing:
        raise StageError(f"release/ lacks {missing}")
    if PROTECTED in files:
        kept = []
        for line in (root / PROTECTED).read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                rel = line.split(None, 1)[1].strip()
                if rel not in out:
                    continue
            kept.append(line)
        out[PROTECTED] = ("\n".join(kept) + "\n").encode()
    if SUMS in out:
        raise StageError(f"{SUMS} would be overwritten")
    return out


def sums_text(files: dict[str, bytes]) -> str:
    return "".join(f"{sha256(b)}  {p}\n" for p, b in sorted(files.items()))


def write_zip(files: dict[str, bytes], out: Path) -> None:
    files = dict(files)
    files[SUMS] = sums_text(files).encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in sorted(files):
            info = zipfile.ZipInfo(f"{TOP}/{p}", EPOCH)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, files[p])
    tmp.replace(out)


# ------------------------------------------------------------------------------------------------ verification
def read_zip(path: Path) -> dict[str, bytes]:
    out = {}
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir():
                raise StageError(f"directory entry {name!r} (the package has file entries only)")
            if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                raise StageError(f"unsafe entry path {name!r}")
            if not name.startswith(TOP + "/"):
                raise StageError(f"entry outside {TOP}/: {name!r}")
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise StageError(f"symbolic link {name!r}")
            out[name[len(TOP) + 1:]] = z.read(info)
    return out


def _text(rel: str, b: bytes) -> str | None:
    if rel.endswith(".gz"):
        b = gzip.decompress(b)
    elif rel.endswith((".npz", ".pdf", ".png")):
        return None
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _keys(obj, found: set) -> None:
    if isinstance(obj, dict):
        found |= set(obj)
        for v in obj.values():
            _keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, found)


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def leak_strings(source: Path) -> set[str]:
    """Answer and response strings of the source logs, normalised, at least MIN_LEAK_CHARS long."""
    out = set()
    for log in sorted(source.glob(GEN_LOG)):
        for line in log.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            for s in list(r.get("answers") or []) + [r.get("response")]:
                if isinstance(s, str) and len(_norm(s)) >= MIN_LEAK_CHARS:
                    out.add(_norm(s))
    return out


def package_ids(files: dict[str, bytes]) -> set[str]:
    """The dataset question IDs the package uses as keys (query lists, job metadata, metrics rows)."""
    ids = set()
    for p, b in files.items():
        if p.endswith(("queries.json", "jobs_meta.json")):
            ids |= set(json.loads(b).get("qids") or [])
        elif p.endswith(MF.SUFFIX):
            ids |= {json.loads(line)["qid"] for line in b.decode().splitlines() if line.strip()}
    return ids | {x.split(":", 1)[-1] for x in ids}


def strip_ids(text: str, ids: set[str]) -> str:
    """Remove quoted question IDs and job IDs (qid|chunking|op): they are disclosed as identifiers, and CUAD's embed
    the contract's file name and title, which can also be a gold answer."""
    return QUOTED.sub(lambda m: " " if m.group(1).split("|", 1)[0] in ids else m.group(0), text)


def _shingles(text: str) -> set[int]:
    t = TOKEN.findall(text.lower())
    return {hash(" ".join(t[i:i + SHINGLE])) for i in range(len(t) - SHINGLE + 1)
            if not all(w.isdigit() for w in t[i:i + SHINGLE])}


def copied_text(texts: dict[str, str], data_root: Path, ids: set[str]) -> dict[str, int]:
    """Entries holding a run of SHINGLE words that also occurs in a dataset document or question, with the count of
    such runs. Dataset question IDs are removed from the entries first (CUAD's embed contract file names); runs of
    digits only are ignored; LICENSE (the standard MIT text, which some CUAD contracts also contain) is not scanned."""
    from ragmv import data as D

    loaded = {d: D.load(d, data_root)[:2] for d in ("squad2", "covidqa", "cuad", "qasper")}
    ids = ids | {x for docs, queries in loaded.values() for q in queries for x in (q.qid, q.qid.split(":", 1)[-1])}
    index: dict[int, set[str]] = {}
    for rel, t in texts.items():
        if rel == "LICENSE":
            continue
        t = strip_ids(t, ids)
        for h in _shingles(t):
            index.setdefault(h, set()).add(rel)
    hits: dict[str, int] = {}
    for docs, queries in loaded.values():
        for text in [d.text for d in docs] + [q.question for q in queries]:
            for h in _shingles(text) & index.keys():
                for rel in index.pop(h):
                    hits[rel] = hits.get(rel, 0) + 1
    return hits


def verify(path: Path, source: Path | None = None, data_root: Path | None = None) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    files = read_zip(path)
    check("entries are files under one top folder, with safe paths and no links", True, f"{len(files)} entries")
    bad_parts = [p for p in files if FORBIDDEN_PARTS & set(Path(p).parts) or p.endswith((".pyc", ".pyo"))]
    check("no Git data, caches or virtual environments", not bad_parts, str(bad_parts[:5]))
    big = [p for p, b in files.items() if len(b) > MAX_ENTRY_BYTES]
    check(f"every entry at most {MAX_ENTRY_BYTES:,} bytes", not big, str(big[:5]))
    listed = {}
    for line in files.get(SUMS, b"").decode().splitlines():
        digest, rel = line.split("  ", 1)
        listed[rel] = digest
    actual = {p: sha256(b) for p, b in files.items() if p != SUMS}
    check(f"{SUMS} lists every entry with its digest", listed == actual,
          f"{len(listed)} listed, {len(actual)} present, "
          f"{len(set(listed) ^ set(actual))} unmatched, {sum(listed.get(p) != d for p, d in actual.items())} differ")
    unruled = []
    for p in actual:
        if p in PACKAGE_FILES:
            continue
        if p.endswith(MF.SUFFIX):
            src = str(Path(p).with_name(MF.source_name(Path(p).name)))
            ok = rule_for(src) == "metrics"
        else:
            ok = rule_for(p) in ("copy", "protected")
        if not ok:
            unruled.append(p)
    check("every entry is allowed by a release rule", not unruled, str(unruled[:5]))
    logs = [p for p in actual if fnmatch.fnmatchcase(p, GEN_LOG) and not p.endswith(MF.SUFFIX)]
    check("no generation log with text", not logs, str(logs[:5]))
    metrics = sorted(p for p in actual if p.endswith(MF.SUFFIX))
    schema_bad, n_rows = [], 0
    for p in metrics:
        for i, line in enumerate(files[p].decode().splitlines(), 1):
            n_rows += 1
            try:
                MF.check_row(json.loads(line), f"{p}:{i}")
            except (ValueError, MF.MetricsFormError) as exc:
                schema_bad.append(str(exc)[:200])
    check("every metrics-only row has exactly the allowlisted fields", metrics and not schema_bad,
          f"{len(metrics)} files, {n_rows} rows; problems: {schema_bad[:3]}")
    texts = {p: t for p, b in files.items() if (t := _text(p, b)) is not None}
    key_hits = []
    for p, t in texts.items():
        if p.startswith("experiments/") and p.endswith((".json", ".jsonl", ".json.gz")):
            found: set = set()
            for chunk in (t.splitlines() if p.endswith(".jsonl") else [t]):
                if chunk.strip():
                    _keys(json.loads(chunk), found)
            if found & FORBIDDEN_KEYS:
                key_hits.append(f"{p}: {sorted(found & FORBIDDEN_KEYS)}")
    check("no experiment record has a text-carrying key", not key_hits, str(key_hits[:5]))
    priv = [p for p, t in texts.items() if PRIVATE_PATH.search(t)]
    check("no private absolute paths", not priv, str(priv[:5]))
    cred = [p for p, t in texts.items() if CREDENTIAL.search(t)]
    check("no credential patterns (values not shown)", not cred, str(cred[:5]))
    if source is not None:
        strings = leak_strings(source)
        ids = package_ids(files)
        normed = {p: _norm(strip_ids(t, ids)) for p, t in texts.items()}
        leaks = sorted({p for s in strings for p, t in normed.items() if s in t})
        check(f"no answer or response string of the source logs (>= {MIN_LEAK_CHARS} chars) in the package",
              strings and not leaks, f"{len(strings)} strings checked; entries containing one: {leaks[:5]}")
    if data_root is not None:
        hits = copied_text(texts, data_root, package_ids(files))
        check(f"no run of {SHINGLE} words copied from a dataset document or question", not hits,
              f"{len(texts)} text entries scanned; hits: {dict(sorted(hits.items(), key=lambda x: -x[1])[:5])}")
    return checks


def recompute(path: Path, python: str = sys.executable) -> list[tuple[str, bool, str]]:
    """Extract the package and rerun its own validation and analyses; compare with its own stored results."""
    checks = []
    runs = [("E1", "ragmv.analyze", "experiments/E1_retrieval_multiverse/runs/confirmatory-20261018",
             "experiments/E1_retrieval_multiverse/analysis/confirmatory-20261018", ["--label", "CONFIRMATORY"]),
            ("E3", "ragmv.analyze1b", "experiments/E3_semantic_dense/runs/confirmatory-kaggle-gpu",
             "experiments/E3_semantic_dense/analysis/confirmatory-kaggle-gpu", ["--label", "CONFIRMATORY"]),
            ("E2", "ragmv.analyze_generation", "experiments/E2_generation/runs/qwen3-4b-kaggle-gpu",
             "experiments/E2_generation/analysis/qwen3-4b-kaggle-gpu", [])]
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(path) as z:
            z.extractall(tmp)
        pkg = Path(tmp) / TOP
        env = {"PYTHONPATH": str(pkg / "src"), "PATH": "/usr/bin:/bin", "HOME": tmp, "MPLCONFIGDIR": tmp,
               "SOURCE_DATE_EPOCH": "1792800000"}

        def run(args, name):
            r = subprocess.run([python, *args], cwd=pkg, env=env, capture_output=True, text=True)
            tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
            checks.append((name, r.returncode == 0, f"exit {r.returncode}; {tail[0][:200]}"))
            return r

        run(["-I", "tools/validate_artifacts.py"], "package: structural validation (tools/validate_artifacts.py)")
        run(["-P", "-m", "pytest", "-q", "-p", "no:cacheprovider"], "package: test suite (without data)")
        for name, mod, run_dir, stored, extra in runs:
            out = Path(tmp) / "recomputed" / name
            run(["-P", "-m", mod, "--run", run_dir, *extra, "--out", str(out)], f"package: {name} analysis reruns")
            r = run(["-I", "tools/compare_results.py", f"{stored}/results.json", str(out / "results.json"),
                     "--inputs-against", SUMS, "--run-dir", run_dir],
                    f"package: {name} recomputed results equal the stored ones; consumed inputs match {SUMS}")
            summary = [x for x in r.stdout.splitlines()
                       if x.startswith(("identical", "different", "missing", "consumed-input"))]
            checks[-1] = (checks[-1][0], checks[-1][1], "; ".join(summary))
        run(["-I", "tools/independent_stats.py", "--out-json", str(Path(tmp) / "ind.json"),
             "--out-md", str(Path(tmp) / "ind.md")], "package: independent statistical checks")
    return checks


def report(checks: list[tuple[str, bool, str]]) -> str:
    lines = ["| Check | Result | Detail |", "|---|---|---|"]
    lines += [f"| {n} | {'PASS' if ok else 'FAIL'} | {d.replace('|', '/')} |" for n, ok, d in checks]
    return "\n".join(lines) + f"\n\n{sum(ok for _, ok, _ in checks)} PASS, {sum(not ok for _, ok, _ in checks)} FAIL\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--allow-dirty", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("zip", type=Path)
    v.add_argument("--source", type=Path, help="checkout with the full generation logs (for the string check)")
    v.add_argument("--data-root", type=Path)
    v.add_argument("--recompute", action="store_true")
    v.add_argument("--report", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "build":
            files = plan(ROOT, args.allow_dirty)
            write_zip(files, args.out)
            print(f"{args.out}: {len(files) + 1} files, {args.out.stat().st_size:,} bytes, "
                  f"sha256 {sha256(args.out.read_bytes())}")
            return 0
        checks = verify(args.zip, args.source, args.data_root)
        if args.recompute:
            checks += recompute(args.zip)
    except (StageError, MF.MetricsFormError, zipfile.BadZipFile) as exc:
        print(f"stage_release: {exc}", file=sys.stderr)
        return 1
    md = report(checks)
    if args.report:
        args.report.write_text(md)
    print(md)
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
