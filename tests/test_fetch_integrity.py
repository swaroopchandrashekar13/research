"""Atomic downloads, verified extraction, path traversal refusal, corrupt members never overwritten."""
import hashlib
import io
import tarfile
import zipfile

import pytest
import yaml

from ragmv import fetch as F


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _opener(payloads, fail_after=None):
    def opener(url):
        data = payloads[url]
        if fail_after is not None:
            class Broken(_Resp):
                def read(self, n=-1):
                    if self.tell() >= fail_after:
                        raise ConnectionResetError("connection reset")
                    return super().read(min(n, fail_after - self.tell()) if n > 0 else n)
            return Broken(data)
        return _Resp(data)
    return opener


def _zip(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def _manifest(tmp_path, url, data, members=None, extract=None):
    entry = {"url": url, "path": "data/raw/ds/archive.zip", "sha256": hashlib.sha256(data).hexdigest()}
    if extract:
        entry["extract"] = extract
    if members:
        entry["members"] = {k: {"sha256": hashlib.sha256(v).hexdigest(), "size": len(v)} for k, v in members.items()}
    path = tmp_path / "MANIFEST.yaml"
    path.write_text(yaml.safe_dump({"datasets": {"ds": {"files": [entry]}}}))
    return path


def test_download_extract_and_verify_only(tmp_path):
    member = b'{"data": []}'
    data = _zip({"test.json": member})
    man = _manifest(tmp_path, "u", data, {"test.json": member}, ["test.json"])
    F.fetch(man, root=tmp_path, opener=_opener({"u": data}))
    assert (tmp_path / "data/raw/ds/test.json").read_bytes() == member
    assert not list((tmp_path / "data/raw/ds").glob("*.part"))
    F.fetch(man, root=tmp_path, verify_only=True, opener=None)  # nothing downloaded, nothing written


def test_interrupted_download_leaves_no_file_under_the_final_name(tmp_path):
    data = _zip({"a.json": b"x" * 5000})
    man = _manifest(tmp_path, "u", data)
    with pytest.raises(ConnectionResetError):
        F.fetch(man, root=tmp_path, opener=_opener({"u": data}, fail_after=100))
    folder = tmp_path / "data/raw/ds"
    assert not (folder / "archive.zip").exists() and not list(folder.glob("*.part"))


def test_wrong_download_digest_writes_nothing(tmp_path):
    data = _zip({"a.json": b"1"})
    man = _manifest(tmp_path, "u", data)
    with pytest.raises(F.IntegrityError, match="nothing was written"):
        F.fetch(man, root=tmp_path, opener=_opener({"u": data + b"tampered"}))
    assert not (tmp_path / "data/raw/ds/archive.zip").exists()


def test_existing_corrupt_file_is_never_overwritten(tmp_path):
    data = _zip({"a.json": b"1"})
    man = _manifest(tmp_path, "u", data)
    target = tmp_path / "data/raw/ds/archive.zip"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"corrupt")
    with pytest.raises(F.IntegrityError, match="left untouched"):
        F.fetch(man, root=tmp_path, opener=_opener({"u": data}))
    assert target.read_bytes() == b"corrupt"


def test_corrupt_extracted_member_is_an_actionable_error_and_kept(tmp_path):
    member = b'{"ok": 1}'
    data = _zip({"test.json": member})
    man = _manifest(tmp_path, "u", data, {"test.json": member}, ["test.json"])
    F.fetch(man, root=tmp_path, opener=_opener({"u": data}))
    extracted = tmp_path / "data/raw/ds/test.json"
    extracted.write_bytes(b'{"ok": 2}')  # silently corrupted member
    with pytest.raises(F.IntegrityError, match="extracted member"):
        F.fetch(man, root=tmp_path, opener=_opener({"u": data}))
    assert extracted.read_bytes() == b'{"ok": 2}'


def test_member_without_recorded_digest_is_checked_against_the_verified_archive(tmp_path):
    data = _zip({"test.json": b"good"})
    man = _manifest(tmp_path, "u", data, None, ["test.json"])
    F.fetch(man, root=tmp_path, opener=_opener({"u": data}))
    (tmp_path / "data/raw/ds/test.json").write_bytes(b"bad!")
    with pytest.raises(F.IntegrityError):
        F.fetch(man, root=tmp_path, opener=_opener({"u": data}))


@pytest.mark.parametrize("name", ["../evil.json", "sub/evil.json", "/abs.json", ".."])
def test_path_traversal_member_names_are_refused(tmp_path, name):
    data = _zip({"x": b"1"})
    man = _manifest(tmp_path, "u", data, None, [name])
    with pytest.raises(F.IntegrityError, match="flat member names"):
        F.fetch(man, root=tmp_path, opener=_opener({"u": data}))
    assert not (tmp_path / "evil.json").exists() and not (tmp_path / "data/raw/evil.json").exists()


def test_tar_symlink_member_is_refused(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        info = tarfile.TarInfo("link.json")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        t.addfile(info)
    data = buf.getvalue()
    entry = {"url": "u", "path": "data/raw/ds/a.tgz", "sha256": hashlib.sha256(data).hexdigest(), "extract": ["link.json"]}
    man = tmp_path / "M.yaml"
    man.write_text(yaml.safe_dump({"datasets": {"ds": {"files": [entry]}}}))
    with pytest.raises(F.IntegrityError, match="not a regular file"):
        F.fetch(man, root=tmp_path, opener=_opener({"u": data}))
    assert not (tmp_path / "data/raw/ds/link.json").exists()


def test_verify_consumed_checks_the_exact_loader_inputs(tmp_path):
    member = b"[]"
    data = _zip({"test.json": member})
    man = _manifest(tmp_path, "u", data, {"test.json": member}, ["test.json"])
    F.fetch(man, root=tmp_path, opener=_opener({"u": data}))
    got = F.verify_consumed("ds", tmp_path / "data/raw", man)
    assert got == {"ds/test.json": hashlib.sha256(member).hexdigest()}
    (tmp_path / "data/raw/ds/test.json").write_bytes(b"[1]")
    with pytest.raises(F.IntegrityError):
        F.verify_consumed("ds", tmp_path / "data/raw", man)


def test_repository_manifest_has_member_digests_for_every_extracted_file():
    from pathlib import Path

    spec = F.load_manifest(Path(__file__).resolve().parents[1] / "data" / "MANIFEST.yaml")
    for name, ds in spec.items():
        for f in ds["files"]:
            for m in f.get("extract", []):
                assert len(f["members"][m]["sha256"]) == 64, (name, m)
