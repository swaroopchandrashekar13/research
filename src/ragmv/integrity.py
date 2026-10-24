"""Integrity helpers shared by the runners: content digests, canonical fingerprints, atomic writes, run locks.

New runs identify their code by a **content digest** of the source tree (never by a version-control commit), and
identify their configuration by a canonical-JSON fingerprint, so a run directory can refuse incompatible reuse.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(obj) -> str:
    """SHA-256 of the canonical JSON encoding of `obj`."""
    return sha256_bytes(canonical_json(obj).encode("utf-8"))


def source_digest(root: Path = PACKAGE_DIR, modules: list[str] | None = None) -> dict:
    """Content identity of the code: SHA-256 over (relative path, NUL, bytes, NUL) of each module, sorted by path.

    `modules` restricts the digest to the files that can change a given output (e.g. the generation path)."""
    names = sorted(modules) if modules else sorted(p.name for p in Path(root).glob("*.py"))
    h = hashlib.sha256()
    per_file = {}
    for name in names:
        data = (Path(root) / name).read_bytes()
        per_file[name] = sha256_bytes(data)
        h.update(name.encode() + b"\0" + data + b"\0")
    return {"sha256": h.hexdigest(), "files": per_file}


def text_list_digest(texts: list[str]) -> str:
    """Order-sensitive digest of a list of strings (length-prefixed, so no separator can collide)."""
    h = hashlib.sha256()
    h.update(str(len(texts)).encode() + b"\n")
    for t in texts:
        b = t.encode("utf-8")
        h.update(str(len(b)).encode() + b":" + b)
    return h.hexdigest()


def atomic_write_bytes(path: str | Path, data: bytes) -> None:
    """Write via a temporary file in the same directory, fsync, then rename: readers never see a partial file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def atomic_write_text(path: str | Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def create_exclusive(path: str | Path, text: str) -> None:
    """Create a file that must not exist yet (immutable start records); raises FileExistsError otherwise."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())


class RunLockError(RuntimeError):
    pass


class RunLock:
    """Exclusive, non-blocking lock on `<dir>/run.lock`, so two processes never write the same run directory.

    POSIX: `fcntl.flock`, released automatically if the process dies. Elsewhere: an O_EXCL lock file that a crashed
    process leaves behind; the error message says how to remove it after checking no writer is alive."""

    def __init__(self, directory: str | Path):
        self.path = Path(directory) / "run.lock"
        self._fh = None
        self._excl = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import fcntl
        except ImportError:  # pragma: no cover - non-POSIX
            try:
                create_exclusive(self.path, str(os.getpid()))
            except FileExistsError as exc:
                raise RunLockError(f"{self.path} exists: another writer may be active. If none is running, delete "
                                   "the lock file and retry.") from exc
            self._excl = True
            return self
        self._fh = open(self.path, "a+")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self._fh.close()
            self._fh = None
            raise RunLockError(f"{self.path} is locked by another process; refusing to write the same run "
                               "directory concurrently") from exc
        return self

    def __exit__(self, *exc):
        if self._fh is not None:
            import fcntl

            fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()
        if self._excl:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(self.path)
        return False


def environment_record() -> dict:
    import platform
    from importlib import metadata

    pkgs = {}
    for pkg in ("numpy", "bm25s", "PyStemmer", "scipy", "statsmodels", "PyYAML", "torch", "transformers",
                "sentence-transformers", "llama_cpp_python", "google-genai", "huggingface_hub"):
        try:
            pkgs[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            pkgs[pkg] = None
    return {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine(),
            "packages": pkgs}


def diff_fields(old: dict, new: dict, prefix: str = "") -> list[str]:
    """Human-readable list of fields that differ between two nested dicts."""
    out = []
    for k in sorted(set(old) | set(new)):
        a, b = old.get(k, "<missing>"), new.get(k, "<missing>")
        if isinstance(a, dict) and isinstance(b, dict):
            out += diff_fields(a, b, f"{prefix}{k}.")
        elif a != b:
            out.append(f"{prefix}{k}: {str(a)[:80]!s} -> {str(b)[:80]!s}")
    return out
