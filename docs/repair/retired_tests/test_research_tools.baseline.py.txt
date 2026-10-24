import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "research")]

import check_bibliography as bib  # noqa: E402
import scoring  # noqa: E402


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


def _toy():
    criteria = {"good": {"weight": 1}, "cost": {"weight": 1, "invert": True}}
    candidates = {
        "A": {"title": "a", "scores": {"good": 5, "cost": 1}},
        "B": {"title": "b", "scores": {"good": 1, "cost": 5}},
    }
    return criteria, candidates


def test_inverted_criteria_and_normalisation():
    criteria, candidates = _toy()
    ids, raw = scoring.score_matrix(criteria, candidates)
    assert raw.tolist() == [[5, 5], [1, 1]]
    s = scoring.weighted(raw, np.array([1.0, 1.0]))
    assert s.tolist() == pytest.approx([100.0, 20.0])


def test_out_of_range_scores_rejected():
    criteria, candidates = _toy()
    candidates["A"]["scores"]["good"] = 6
    with pytest.raises(ValueError):
        scoring.score_matrix(criteria, candidates)


def test_real_matrix_ranks_deterministically():
    criteria, candidates = scoring.load(ROOT / "research" / "opportunity_matrix.yaml")
    assert scoring.rank_table(criteria, candidates) == scoring.rank_table(criteria, candidates)
    assert all(set(c["scores"]) == set(criteria) for c in candidates.values())
