"""F-005: operator claims must never occupy solver-derived columns.

An independent certifier posted invented facilities, an invented OSRM hash and 100%
coverage to POST /decisions and received 201 with a persisted decision_id. Requiring
the fields stopped an empty body; declaring the decision MANUAL_OPERATOR_DECISION
improved labelling. Neither stopped caller numbers occupying the authoritative
columns, so every downstream reader still treated them as computed.
"""

from __future__ import annotations

import inspect

import pytest

from services.api.routers import observatory
from services.zonepilot.decisions.ledger import DecisionLedger
from services.zonepilot.decisions.lineage_validation import (
    UNVERIFIED,
    VERIFIED,
    canonical_facility_ids,
    operator_claims,
    validate_operator_lineage,
)

FORGED_FACILITIES = ["fac:does-not-exist", "fac:also-fake"]


def test_invented_facilities_are_rejected() -> None:
    """The certifier's exact payload: facilities that resolve nowhere."""
    verdict = validate_operator_lineage(
        opened_facilities=FORGED_FACILITIES,
        graph_version="not-a-graph",
        osrm_bundle_hash="0" * 64,
    )
    assert not verdict.ok
    assert "does-not-exist" in "; ".join(verdict.rejections)


def test_real_facilities_are_accepted() -> None:
    """Control: without this, rejection could be unconditional."""
    known = sorted(canonical_facility_ids())
    verdict = validate_operator_lineage(opened_facilities=known[:2], graph_version=None, osrm_bundle_hash=None)
    assert verdict.ok
    assert verdict.verified["opened_facilities"] == VERIFIED


def test_forged_hash_is_marked_not_silently_trusted() -> None:
    """A version or hash claim is recorded with its verdict, never assumed true."""
    known = sorted(canonical_facility_ids())
    verdict = validate_operator_lineage(
        opened_facilities=known[:1],
        graph_version="not-a-graph",
        osrm_bundle_hash="0" * 64,
    )
    assert verdict.ok, "a wrong version is a mismatch to record, not a reason to reject"
    assert verdict.verified["graph_version"] == "MISMATCH"
    assert verdict.verified["osrm_bundle_hash"] in {"MISMATCH", UNVERIFIED}


def test_operator_claims_are_never_derived() -> None:
    claims = operator_claims(
        objective_value=1,
        expected_travel_seconds=0,
        p95_travel_seconds=0,
        coverage_basis_points=10_000,
    )
    assert set(claims) == {
        "objective_value",
        "expected_travel_seconds",
        "p95_travel_seconds",
        "coverage_basis_points",
    }
    for entry in claims.values():
        assert entry["evidence_class"] == UNVERIFIED
        assert entry["evidence_class"] not in {"DERIVED", "OBSERVED", "PUBLIC_GEOGRAPHIC"}


def test_router_sends_none_to_the_derived_columns() -> None:
    """The manual path must not forward caller metrics into authoritative fields."""
    src = inspect.getsource(observatory.record_decision)
    tail = src[src.index("_dec_ledger.record_decision") :]
    for field in (
        "objective_value=None",
        "expected_travel_seconds=None",
        "p95_travel_seconds=None",
        "coverage_basis_points=None",
    ):
        assert field in tail, f"manual path must pass {field}"
    assert "operator_claims=" in tail
    assert "lineage_verified=" in tail


def test_optimizer_decision_still_requires_every_derived_metric() -> None:
    """Nullability exists for the manual class only; it must not become a loophole."""
    ledger = DecisionLedger.__new__(DecisionLedger)
    with pytest.raises(ValueError) as exc:
        DecisionLedger.record_decision(
            ledger,
            workspace_id="ws-1",
            decision_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            network_version="1.1",
            dataset_version="1.0.0",
            feature_snapshot_hash="a" * 64,
            selected_action="OPEN_FACILITIES",
            opened_facilities=["fac:01"],
            objective_value=None,
            expected_travel_seconds=None,
            p95_travel_seconds=None,
            coverage_basis_points=None,
            graph_version="1.1",
            osrm_bundle_hash="b" * 64,
            solver_version="ortools-cp-sat",
        )
    assert "OPTIMIZER_DECISION requires every derived metric" in str(exc.value)
