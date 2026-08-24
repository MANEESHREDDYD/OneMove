"""Every demand zone in a solved problem must be accountable.

A 94-zone problem that returned four assignments and left the other ninety
invisible was reported as `OPTIMAL`. It was arithmetically optimal and
operationally meaningless: 11.46% of demand served. These tests pin the
accounting so that outcome can never again be reported without the coverage
that qualifies it.

They also pin the two defects found alongside it:
  * an INFEASIBLE result carries `objective: None`, which used to raise
    AttributeError in the read path and surface as HTTP 500;
  * zero travel is only legitimate where a facility and a demand point occupy
    the same H3 cell.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


DATA_ROOT = Path(os.environ.get("ZONEPILOT_DATA_ROOT", "data_root"))
MATRIX = DATA_ROOT / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"


@pytest.fixture(scope="module")
def matrix() -> dict:
    if not MATRIX.is_file():
        pytest.skip(f"authentic travel matrix not mounted at {MATRIX}")
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def test_matrix_dimensions_are_the_authentic_12x94(matrix: dict) -> None:
    """The canonical problem shape must not drift."""
    assert len(matrix["facility_ids"]) == 12
    assert len(matrix["demand_ids"]) == 94
    assert len(matrix["base_durations_seconds"]) == 12
    for row in matrix["base_durations_seconds"]:
        assert len(row) == 94


def test_zero_travel_only_for_genuine_self_loops(matrix: dict) -> None:
    """Zero seconds is valid only where facility and demand share an H3 cell.

    A silent zero on an unrelated pair would let the solver serve a distant zone
    for free, which is exactly how a meaningless assignment becomes attractive.
    """
    facilities = [f.removeprefix("fac:") for f in matrix["facility_ids"]]
    demands = [d.removeprefix("zone:") for d in matrix["demand_ids"]]
    durations = matrix["base_durations_seconds"]

    zero_pairs = [
        (facilities[i], demands[j])
        for i in range(len(facilities))
        for j in range(len(demands))
        if durations[i][j] == 0
    ]
    for facility_cell, demand_cell in zero_pairs:
        assert facility_cell == demand_cell, (
            f"zero travel between distinct cells {facility_cell} -> {demand_cell}"
        )

    # Every facility must have exactly one self-loop, and it must be zero.
    for i, facility_cell in enumerate(facilities):
        if facility_cell in demands:
            j = demands.index(facility_cell)
            assert durations[i][j] == 0

    assert len(zero_pairs) == 12, "expected exactly one zero self-loop per facility"


def test_non_zero_durations_survive_reconstruction(matrix: dict) -> None:
    """Routed durations must stay non-zero; a collapse to zero is a silent bug."""
    durations = matrix["base_durations_seconds"]
    flat = [d for row in durations for d in row]
    non_zero = [d for d in flat if d > 0]
    assert len(non_zero) == len(flat) - 12
    assert min(non_zero) > 0
    assert all(isinstance(d, int) and d >= 0 for d in flat)


def _coverage_summary(*args, **kwargs):
    from services.api.routers.observatory import _coverage_summary

    return _coverage_summary(*args, **kwargs)


def test_every_zone_is_assigned_or_uncovered() -> None:
    """assigned + uncovered must equal the problem's full demand set."""
    snapshot = {
        "problem": {
            "demand_points": [{"demand_id": f"zone:{i:03d}", "demand_units": 10} for i in range(94)]
        }
    }
    res_doc = {
        "assignments": [
            {"demand_id": "zone:000", "facility_id": "fac:000", "scenario_id": "s1", "travel_seconds": 0},
            {"demand_id": "zone:001", "facility_id": "fac:001", "scenario_id": "s1", "travel_seconds": 0},
        ],
        "scenario_metrics": [
            {"scenario_id": "s1", "covered_demand_units": 20, "uncovered_demand_units": 920,
             "coverage_basis_points": 212, "probability_basis_points": 10000},
        ],
    }
    summary = _coverage_summary(res_doc["scenario_metrics"], res_doc, snapshot)

    assert summary["demand_zones_total"] == 94
    assert summary["assigned_zones"] == 2
    assert summary["uncovered_zones"] == 92
    assert summary["assigned_zones"] + summary["uncovered_zones"] == summary["demand_zones_total"]
    assert len(summary["uncovered_zone_ids"]) == 92
    assert "zone:000" not in summary["uncovered_zone_ids"]


def test_coverage_reports_the_worst_scenario() -> None:
    """A service commitment is bound by the worst scenario, not the average."""
    snapshot = {"problem": {"demand_points": [{"demand_id": "zone:000", "demand_units": 10}]}}
    res_doc = {"assignments": [{"demand_id": "zone:000"}]}
    metrics = [
        {"scenario_id": "s1", "coverage_basis_points": 9000, "covered_demand_units": 90, "uncovered_demand_units": 10},
        {"scenario_id": "s3", "coverage_basis_points": 1146, "covered_demand_units": 11, "uncovered_demand_units": 89},
    ]
    summary = _coverage_summary(metrics, res_doc, snapshot)
    assert summary["coverage_basis_points"] == 1146
    assert summary["uncovered_demand_units"] == 89


def test_infeasible_result_is_readable_not_a_crash() -> None:
    """`objective: None` must not raise; INFEASIBLE is a legitimate outcome.

    The read path used to test `"objective" in res_doc` and then call `.get` on
    the value, so a proven-infeasible job returned HTTP 500 instead of its
    typed state.
    """
    res_doc = {
        "status": "INFEASIBLE",
        "action": "NONE",
        "objective": None,
        "assignments": [],
        "scenario_metrics": [],
    }
    summary = _coverage_summary([], res_doc, None)

    assert summary["coverage_basis_points"] is None
    assert summary["uncovered_zone_ids"] == []
    # The important property: it returned instead of raising.
    objective = res_doc.get("objective") or {}
    assert objective.get("expected_travel_probability_demand_seconds") is None


def test_no_snapshot_degrades_without_inventing_counts() -> None:
    """Without the frozen problem, zone counts are unknown - not zero."""
    res_doc = {"assignments": [{"demand_id": "zone:000"}], "scenario_metrics": []}
    summary = _coverage_summary([], res_doc, None)
    assert summary["demand_zones_total"] is None
    assert summary["uncovered_zones"] is None
