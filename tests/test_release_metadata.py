"""Release metadata: the two files agree, ORCID iDs are checked digit by digit, and --set-orcid writes only a valid iD."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_release_metadata as M  # noqa: E402

VALID = "0000-0002-1825-0097"  # the example iD of ORCID's own documentation


def test_orcid_check_digit():
    assert M.orcid_ok(VALID) and M.orcid_ok("0000-0002-9079-593X")
    assert not M.orcid_ok("0000-0002-1825-0098") and not M.orcid_ok("0000-0002-1825-009")


def test_repository_metadata_passes_and_reports_missing_identifiers():
    assert M.main([]) == 0


@pytest.fixture
def copies(tmp_path, monkeypatch):
    for name in ("CITATION.cff", ".zenodo.json", "LICENSE", "LICENSE-DATA.md"):
        shutil.copy(ROOT / name, tmp_path / name)
    monkeypatch.setattr(M, "ROOT", tmp_path)
    monkeypatch.setattr(M, "CFF", tmp_path / "CITATION.cff")
    monkeypatch.setattr(M, "ZEN", tmp_path / ".zenodo.json")
    return tmp_path


def test_set_orcid_writes_both_files(copies):
    assert M.main(["--set-orcid", VALID]) == 0
    assert f'orcid: "https://orcid.org/{VALID}"' in (copies / "CITATION.cff").read_text()
    assert json.loads((copies / ".zenodo.json").read_text())["creators"][0]["orcid"] == VALID


def test_invalid_orcid_is_refused_and_nothing_changes(copies):
    before = (copies / "CITATION.cff").read_text()
    with pytest.raises(SystemExit, match="not a valid ORCID"):
        M.main(["--set-orcid", "0000-0002-1825-0098"])
    assert (copies / "CITATION.cff").read_text() == before


@pytest.mark.parametrize("edit, expect", [
    (lambda c, z: c.replace('given-names: "Swaroop"', 'given-names: "S."'), "authors differ"),
    (lambda c, z: c + 'repository-code: "https://github.com/someone/somewhere"\n', "repository-hosting URL"),
    (lambda c, z: c + 'doi: "TODO"\n', "placeholder"),
])
def test_inconsistent_metadata_fails(copies, capsys, edit, expect):
    cff = copies / "CITATION.cff"
    cff.write_text(edit(cff.read_text(), None))
    assert M.main([]) == 1
    assert expect in capsys.readouterr().out
