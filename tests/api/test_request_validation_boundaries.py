"""Request-model boundaries that were only enforced (or not enforced at all) below the API.

Every case here was found by driving the live app with hostile input. They share
one shape: an invariant that the domain, the driver or the database already
holds is missing from the request model, so a permanent client mistake is either
accepted and durably persisted, or reported as a retryable 5xx.

The contract these tests pin is the one the router already states for itself in
`_fail_if_dependency_unavailable`: a dependency outage is a retryable 503, and a
client mistake is a typed, non-retryable 4xx. Nothing in between.

None of these tests may reach the store. A request that is rejected correctly is
rejected before anything is written, which is the property `_never_persists`
asserts directly.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app
from services.api.routers import observatory

ENVELOPE_FIELDS = {"code", "message", "retryable", "details", "request_id", "trace_id"}

WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-000000000002"

VALID_H3_CELL = "88618925d3fffff"


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": USER_ID,
        "workspace_id": WORKSPACE_ID,
        "role": "operator",
    }
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def never_persists(monkeypatch: pytest.MonkeyPatch):
    """Fail loudly if a rejected request still reached a durable writer."""
    written: list[object] = []

    def _forbidden(*args, **kwargs):
        written.append((args, kwargs))
        raise AssertionError("a rejected request reached the store")

    monkeypatch.setattr(observatory._forecast_repo, "save_prediction", _forbidden)
    monkeypatch.setattr(observatory._opt_service, "submit_optimization", _forbidden)
    return written


def envelope_of(response) -> dict:
    body = response.json()
    assert "error" in body, f"response is not the canonical envelope: {body}"
    error = body["error"]
    assert set(error) >= ENVELOPE_FIELDS, f"missing envelope fields: {ENVELOPE_FIELDS - set(error)}"
    return error


# --- POST /api/v1/forecast/predict : zone_id ---------------------------------


@pytest.mark.parametrize(
    "zone_id",
    [
        "../../etc/passwd",
        "'; DROP TABLE forecast_records;--",
        "not-an-h3",
        "",
        "Z" * 10_240,
        "88618925d3ffffZ",
    ],
    ids=["traversal", "sql-shaped", "arbitrary", "empty", "oversized", "near-miss"],
)
def test_forecast_rejects_any_zone_id_that_is_not_an_h3_cell(
    client: TestClient, never_persists: list, zone_id: str
) -> None:
    """A forecast row keyed to a zone that cannot exist is unfalsifiable garbage.

    `zone_id` was a bare `str`, so the endpoint returned 201 and wrote the value
    into `forecast_records` verbatim -- including `../../etc/passwd`. The table
    is a measurement table; once such a row exists nothing distinguishes it from
    a real one, because nothing recorded that the zone was never validated.
    """
    response = client.post("/api/v1/forecast/predict", json={"zone_id": zone_id})

    assert response.status_code == 422, response.text
    error = envelope_of(response)
    assert error["code"] == "INVALID_ARGUMENT"
    assert error["retryable"] is False


def test_forecast_zone_id_rejection_matches_the_zone_state_route(client: TestClient, never_persists: list) -> None:
    """The read path and the write path must agree on what a zone id is.

    GET /zones/{zone_id}/state has always rejected a non-H3 id with this exact
    message. The forecast write path accepted what the read path refused.
    """
    response = client.post("/api/v1/forecast/predict", json={"zone_id": "not-an-h3"})

    assert envelope_of(response)["message"] == "Zone ID must be a valid H3 cell identifier"


# --- POST /api/v1/optimizations : scenarios -----------------------------------


@pytest.mark.parametrize(
    "scenarios",
    [
        ["totally_made_up_a", "totally_made_up_b", "totally_made_up_c"],
        ["s3_congested_outage", "s2_congested", "s1_free_flow"],
        ["s1_free_flow", "s1_free_flow", "s1_free_flow"],
        ["s1_free_flow", "s2_congested", "matrix-s1_free_flow"],
    ],
    ids=["invented", "reordered", "repeated-baseline", "near-miss"],
)
def test_optimization_refuses_scenario_ids_the_ladder_does_not_define(
    client: TestClient, never_persists: list, scenarios: list[str]
) -> None:
    """A scenario id is the label on a sealed uncertainty tier, not a free string.

    `scenarios: list[str]` was unvalidated and the builder only checked the
    *count* before zipping the caller's strings positionally onto the assumption
    set's tiers, stamping each with that tier's probability, duration multiplier
    and `evidence_class`. So any three strings validated, and the SEVERE tier's
    1.4x multiplier and SIMULATED_FAILURE evidence class could be attached to a
    matrix named `matrix-s1_free_flow`.

    That is not a cosmetic mislabel: the id becomes the `matrix_id` on the frozen
    problem, which is covered by `problem_fingerprint` and therefore propagates
    into the job row, the problem snapshot, the result document and any decision
    frozen from it. It was the one label on a frozen artifact that nothing
    validated, so an audit reading the ledger back could not tell whether
    `matrix-s1_free_flow` was free-flow.

    The `reordered` case matters most: every id in it is real, so a check that
    only tested membership would pass it while the labels still landed on the
    wrong rungs.
    """
    response = client.post("/api/v1/optimizations", json={"scenarios": scenarios})

    assert response.status_code == 422, response.text
    error = envelope_of(response)
    assert error["code"] == "SCENARIO_UNKNOWN"
    assert error["retryable"] is False
    # The sibling POST /api/v1/scenarios enumerates its legal values; so must this.
    for accepted in ("s1_free_flow", "s2_congested", "s3_congested_outage"):
        assert accepted in error["message"]


def test_optimization_scenario_count_mismatch_is_typed_and_not_retryable(
    client: TestClient, never_persists: list
) -> None:
    """The count check existed but escaped as a bare ValueError -> 500 retryable:true."""
    response = client.post("/api/v1/optimizations", json={"scenarios": []})

    assert response.status_code == 422, response.text
    error = envelope_of(response)
    assert error["code"] == "SCENARIO_LADDER_MISMATCH"
    assert error["retryable"] is False


def test_scenario_labels_belong_to_the_tier_not_the_request() -> None:
    """The structural half: the ladder owns its labels.

    Asserted directly against the assumption set so the guarantee cannot be
    satisfied by an API-layer allow-list that a second writer (the Pub/Sub
    worker's payload reconstruction) would bypass.
    """
    from services.zonepilot.assumptions.application import CANONICAL_SCENARIO_IDS
    from services.zonepilot.assumptions.registry import default_assumption_registry

    view = default_assumption_registry().active_view()
    tiers = view.scenario_tiers

    assert tuple(tier.scenario_id for tier in tiers) == CANONICAL_SCENARIO_IDS
    # The baseline rung is the one whose matrix is real routed geography.
    assert tiers[0].is_baseline and tiers[0].scenario_id == "s1_free_flow"

    bound = view.bind_scenarios(list(CANONICAL_SCENARIO_IDS))
    assert bound == tiers


def test_worker_reconstruction_refuses_an_unbound_scenario_label() -> None:
    """The second writer must refuse what the API refuses.

    `_reconstruct_problem_from_payload` re-solves a frozen payload. Validating
    only at submission would leave this path re-attaching invented labels to the
    sealed tiers for any job whose payload predates the fix.
    """
    from services.zonepilot.assumptions.application import ScenarioBindingError
    from services.zonepilot.optimization.pubsub_worker import _reconstruct_problem_from_payload

    with pytest.raises(ScenarioBindingError) as raised:
        _reconstruct_problem_from_payload({"scenarios": ["a", "b", "c"]})
    assert raised.value.code == "SCENARIO_UNKNOWN"

    try:
        problem = _reconstruct_problem_from_payload({})
    except FileNotFoundError as exc:  # pragma: no cover - artifact-dependent
        pytest.skip(f"R1 evidence artifacts unavailable: {exc}")
    assert [s.scenario_id for s in problem.scenarios] == ["s1_free_flow", "s2_congested", "s3_congested_outage"]
