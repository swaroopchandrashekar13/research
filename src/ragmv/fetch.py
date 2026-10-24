"""Download datasets listed in data/MANIFEST.yaml and verify their SHA256 hashes.

Usage: python -I -m ragmv.fetch [--manifest data/MANIFEST.yaml] [--only squad2 covidqa ...]
Archives are extracted member-by-member (only the members named in the manifest), never with extractall.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _extract(archive: Path, members: list[str]) -> None:
    dest = archive.parent
    for name in members:
        if Path(name).name != name:  # flat member names only; refuses path traversal
            raise ValueError(f"refusing nested archive member {name!r}")
        target = dest / name
        if target.exists():
            continue
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive) as z, z.open(name) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
        else:
            with tarfile.open(archive) as t:
                src = t.extractfile(t.getmember(name))
                with open(target, "wb") as out:
                    shutil.copyfileobj(src, out)


def fetch(manifest: Path, only: list[str] | None = None, root: Path = Path(".")) -> None:
    spec = yaml.safe_load(manifest.read_text())["datasets"]
    for name, ds in spec.items():
        if only and name not in only:
            continue
        for f in ds["files"]:
            path = root / f["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                print(f"downloading {f['url']}")
                urllib.request.urlretrieve(f["url"], path)
            digest = sha256(path)
            if digest != f["sha256"]:
                raise RuntimeError(f"{path}: sha256 {digest} != manifest {f['sha256']}")
            _extract(path, f.get("extract", []))
            print(f"ok {name}: {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="data/MANIFEST.yaml")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    fetch(Path(args.manifest), args.only)


if __name__ == "__main__":
    main()
