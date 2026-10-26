"""Bibliography validator tests."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import check_bibliography as bib  # noqa: E402


def test_bibliography_file_is_valid():
    entries = bib.load(ROOT / "literature" / "bibliography.yaml")
    assert bib.validate(entries) == []


def test_validator_rejects_l0_duplicates_and_missing_fields():
    entries = [
        {"key": "a", "title": "t", "year": 2024, "venue": "v", "verification": "L0", "directions": ["C1"], "url": "u"},
        {"key": "a", "title": "t", "year": 2024, "venue": "v", "verification": "L1", "directions": ["C1"]},
    ]
    errors = " ".join(bib.validate(entries))
    assert "L0 entries" in errors and "duplicate key" in errors and "url or an id" in errors


def test_citation_gate_blocks_under_verified_sources():
    entries = [{"key": "x", "verification": "L1"}, {"key": "y", "verification": "L3"}]
    assert bib.citable(entries, ["y"], "L2") == []
    assert "verified only to L1" in bib.citable(entries, ["x"], "L2")[0]
    assert "not in bibliography" in bib.citable(entries, ["z"], "L2")[0]
