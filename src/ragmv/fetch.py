"""Download datasets listed in data/MANIFEST.yaml and verify the exact bytes the loaders consume.

Usage:
  python -I -m ragmv.fetch [--manifest data/MANIFEST.yaml] [--root .] [--only squad2 covidqa ...]
  python -I -m ragmv.fetch --verify-only        # check files already on disk; never downloads or writes

Guarantees:
- Downloads go to a temporary `.part` file in the target directory and are renamed into place only after their
  SHA-256 matches the manifest, so an interrupted or corrupted download never appears under the final name.
- An existing file whose digest differs is **never overwritten or deleted**: the command stops and says what to do.
- Archives are extracted member by member (only the members named in the manifest), never with extractall. A member
  must be a flat, regular file (no directories, links, devices or path components). Extracted members are checked
  against the manifest's member digests (or, for members without a recorded digest, against the bytes inside the
  verified archive), written atomically, and an existing member that differs is a hard error.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

import yaml

from .integrity import sha256_file

MAX_MEMBER_BYTES = 2 << 30  # 2 GiB: refuse absurd (zip-bomb-like) members


class IntegrityError(RuntimeError):
    """A file on disk does not match the manifest; the message names the file and the remedy."""


def sha256(path: Path) -> str:  # kept for callers of the original API
    return sha256_file(path)


def load_manifest(manifest: Path) -> dict:
    return yaml.safe_load(Path(manifest).read_text())["datasets"]


def _mismatch(path: Path, got: str, want: str, what: str) -> IntegrityError:
    return IntegrityError(
        f"{path}: {what} SHA-256 {got} does not match the manifest ({want}). The file was left untouched. Move it "
        f"aside (e.g. `mv '{path}' '{path}.suspect'`) and rerun `python -I -m ragmv.fetch` to download a fresh copy; "
        f"if the upstream file changed, record the new digest in data/MANIFEST.yaml as a dated, documented change.")


def _download(url: str, path: Path, want: str, opener=urllib.request.urlopen) -> None:
    """Stream `url` into a temporary file next to `path`; rename only if the digest matches."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".part", dir=path.parent)
    h = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as out, opener(url) as resp:
            for block in iter(lambda: resp.read(1 << 20), b""):
                h.update(block)
                out.write(block)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(tmp, 0o644)
        got = h.hexdigest()
        if got != want:
            raise IntegrityError(f"download of {url} has SHA-256 {got}, manifest says {want}; nothing was written "
                                 f"to {path}. Retry later or check whether the upstream file changed.")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _safe_member_name(name: str) -> str:
    p = PurePosixPath(name)
    if name != p.name or name in ("", ".", "..") or "\\" in name or name.startswith("/"):
        raise IntegrityError(f"refusing archive member {name!r}: only flat member names are allowed")
    return name


def _member_bytes(archive: Path, name: str) -> bytes:
    """Bytes of one flat, regular member of a verified zip or tar archive."""
    _safe_member_name(name)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            info = z.getinfo(name)
            if info.is_dir() or (info.external_attr >> 16) & 0o170000 not in (0, 0o100000):
                raise IntegrityError(f"{archive}: member {name!r} is not a regular file")
            if info.file_size > MAX_MEMBER_BYTES:
                raise IntegrityError(f"{archive}: member {name!r} is too large ({info.file_size} bytes)")
            return z.read(info)
    with tarfile.open(archive) as t:
        m = t.getmember(name)
        if not m.isreg():
            raise IntegrityError(f"{archive}: member {name!r} is not a regular file (type {m.type!r})")
        if m.size > MAX_MEMBER_BYTES:
            raise IntegrityError(f"{archive}: member {name!r} is too large ({m.size} bytes)")
        src = t.extractfile(m)
        return src.read()


def _extract(archive: Path, members: list[str], digests: dict | None = None, verify_only: bool = False) -> list[str]:
    """Extract `members` next to `archive` (already hash-verified). Returns status lines."""
    digests = digests or {}
    out = []
    for name in members:
        _safe_member_name(name)
        target = archive.parent / name
        want = (digests.get(name) or {}).get("sha256")
        if target.exists():
            got = sha256_file(target)
            expect = want or hashlib.sha256(_member_bytes(archive, name)).hexdigest()
            if got != expect:
                raise _mismatch(target, got, expect, "extracted member")
            out.append(f"ok member {target}")
            continue
        if verify_only:
            raise IntegrityError(f"{target} is missing (verify-only mode never extracts); run without --verify-only")
        data = _member_bytes(archive, name)
        got = hashlib.sha256(data).hexdigest()
        if want and got != want:
            raise IntegrityError(f"{archive}: member {name!r} has SHA-256 {got}, manifest says {want}; nothing was "
                                 "written.")
        fd, tmp = tempfile.mkstemp(prefix=f".{name}.", suffix=".part", dir=archive.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, 0o644)
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        out.append(f"extracted {target}")
    return out


def fetch(manifest: Path, only: list[str] | None = None, root: Path = Path("."), verify_only: bool = False,
          opener=urllib.request.urlopen) -> list[str]:
    spec = load_manifest(manifest)
    unknown = sorted(set(only or []) - set(spec))
    if unknown:
        raise SystemExit(f"unknown dataset(s) {unknown}; manifest has {sorted(spec)}")
    log = []
    for name, ds in spec.items():
        if only and name not in only:
            continue
        for f in ds["files"]:
            path = Path(root) / f["path"]
            if path.exists():
                got = sha256_file(path)
                if got != f["sha256"]:
                    raise _mismatch(path, got, f["sha256"], "file")
            elif verify_only:
                raise IntegrityError(f"{path} is missing (verify-only mode never downloads)")
            else:
                print(f"downloading {f['url']}", flush=True)
                _download(f["url"], path, f["sha256"], opener)
            log.append(f"ok {name}: {path}")
            log += _extract(path, f.get("extract", []), f.get("members"), verify_only)
    for line in log:
        print(line)
    return log


def consumed_files(name: str, manifest: Path, root: Path = Path(".")) -> dict[Path, str]:
    """{path: expected SHA-256} of the exact files a loader reads for dataset `name`."""
    ds = load_manifest(manifest)[name]
    out = {}
    for f in ds["files"]:
        path = Path(root) / f["path"]
        if f.get("extract"):
            for m in f["extract"]:
                want = (f.get("members") or {}).get(m, {}).get("sha256")
                if not want:
                    raise IntegrityError(f"{name}: no member digest for {m!r} in the manifest")
                out[path.parent / m] = want
        else:
            out[path] = f["sha256"]
    return out


def verify_consumed(name: str, data_root: Path, manifest: Path | None = None) -> dict[str, str]:
    """Check every file the loader for `name` will read under `data_root`; returns {relative path: sha256}."""
    manifest = Path(manifest) if manifest else Path(__file__).resolve().parents[2] / "data" / "MANIFEST.yaml"
    files = consumed_files(name, manifest, Path("."))
    out = {}
    for rel, want in files.items():
        parts = rel.parts
        rel_to_data = Path(*parts[2:]) if parts[:2] == ("data", "raw") else rel
        path = Path(data_root) / rel_to_data
        if not path.exists():
            raise IntegrityError(f"{path} is missing; run `python -I -m ragmv.fetch` (data root {data_root})")
        got = sha256_file(path)
        if got != want:
            raise _mismatch(path, got, want, "input")
        out[str(rel_to_data)] = got
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/MANIFEST.yaml")
    ap.add_argument("--root", default=".", help="directory that the manifest's relative paths start from")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--verify-only", action="store_true", help="check existing files; never download or write")
    args = ap.parse_args(argv)
    try:
        fetch(Path(args.manifest), args.only, Path(args.root), verify_only=args.verify_only)
    except IntegrityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
