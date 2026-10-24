"""Bibliography validator tests.

The opportunity-scoring tests that used to live here imported `research/scoring.py` and read
`research/opportunity_matrix.yaml`; neither file is in this repository, and the Phase-0 direction-scoring workflow they
tested is obsolete (the study direction was chosen; see docs/reports/R3). They were retired on 2026-10-24 rather than
satisfied by an unrelated `scoring` package or by invented scores. Their source is preserved verbatim in
docs/repair/retired_tests/test_research_tools.baseline.py.txt; the baseline collection error is recorded in
docs/repair/REPAIR_REPORT.md.
"""
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
