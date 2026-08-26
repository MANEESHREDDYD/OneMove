"""Executable enforcement of docs/readiness/regression_guard.yaml.

Each defect named in that manifest was real. This module asserts, against the
CURRENT source, that none of them has come back. It exists specifically to catch
a parallel worktree branched from an older base reintroducing a fixed defect
through a merge that reported no conflicts.

TWO RULES FOR ANYTHING ADDED HERE
---------------------------------
1. Assert against real behaviour or real parsed source. Never assert that a
   string appears in a file when the behaviour itself can be exercised.
2. Every assertion must have been SEEN to fail. Three vacuous tests were found
   in this repository that asserted nothing while reporting green; a guard that
   has never gone red is indistinguishable from one of them.

The manifest and this module are checked against each other by
``test_rg00_manifest_and_tests_are_in_sync``, so a guard cannot be documented
without being enforced, or enforced without being documented.
"""

from __future__ import annotations

import ast
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "docs" / "readiness" / "regression_guard.yaml"

CONTRACTS_PY = REPO_ROOT / "services" / "zonepilot" / "optimization" / "contracts.py"
CP_SAT_PY = REPO_ROOT / "services" / "zonepilot" / "optimization" / "_cp_sat.py"
PUBSUB_WORKER_PY = REPO_ROOT / "services" / "zonepilot" / "optimization" / "pubsub_worker.py"
LEDGER_PY = REPO_ROOT / "services" / "zonepilot" / "decisions" / "ledger.py"
DECISION_REPO_PY = REPO_ROOT / "services" / "zonepilot" / "decisions" / "repository.py"
GEO_LINEAGE_PY = REPO_ROOT / "tests" / "geo" / "test_pilot_roads_lineage.py"
FORECAST_MIGRATION = (
    REPO_ROOT / "supabase" / "migrations" / "20260825001000_forecast_evidence_accumulating.sql"
)


# --- shared helpers ----------------------------------------------------------


def _parse(path: Path) -> ast.Module:
    assert path.is_file(), f"guarded source has been deleted: {path}"
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _find_function(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"guarded function {name!r} no longer exists")


def _find_class(module: ast.Module, name: str) -> ast.ClassDef:
    for node in ast.walk(module):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise AssertionError(f"guarded class {name!r} no longer exists")


# --- RG-00: the manifest and this module describe the same guards ------------


def _manifest_guard_ids() -> list[str]:
    text = MANIFEST.read_text(encoding="utf-8")
    return re.findall(r"^  - id: (RG-\d+)$", text, flags=re.MULTILINE)


def test_rg00_manifest_and_tests_are_in_sync() -> None:
    """A documented guard must be enforced, and an enforced guard documented."""
    assert MANIFEST.is_file(), "the regression guard manifest has been deleted"
    documented = _manifest_guard_ids()
    assert documented, "the manifest declares no guards; it has been emptied"

    module = _parse(Path(__file__))
    enforced = {
        m.group(1).upper()
        for node in module.body
        if isinstance(node, ast.FunctionDef)
        for m in [re.match(r"test_(rg\d+)_", node.name)]
        if m
    }
    enforced.discard("RG00")
    normalised_documented = {gid.replace("-", "") for gid in documented}

    assert normalised_documented == enforced, (
        "manifest and enforcement diverged. "
        f"documented but not enforced: {sorted(normalised_documented - enforced)}; "
        f"enforced but not documented: {sorted(enforced - normalised_documented)}"
    )


# --- RG-01: allow_uncovered_demand defaults to False in all three places -----


def test_rg01_allow_uncovered_demand_defaults_false_in_contract() -> None:
    from services.zonepilot.optimization.contracts import OptimizationConstraints

    field = OptimizationConstraints.model_fields["allow_uncovered_demand"]
    assert field.default is False, (
        "OptimizationConstraints.allow_uncovered_demand no longer defaults to False. "
        "Partial coverage would again be permitted without the operator asking for it."
    )

    built = OptimizationConstraints(
        min_open_facilities=1,
        max_open_facilities=2,
        max_travel_seconds=1800,
        minimum_coverage_basis_points=10_000,
    )
    assert built.allow_uncovered_demand is False


def test_rg01_allow_uncovered_demand_defaults_false_in_api_request() -> None:
    from services.api.routers.observatory import OptimizationRequest

    assert OptimizationRequest().allow_uncovered_demand is False, (
        "The API OptimizationRequest no longer defaults allow_uncovered_demand to False. "
        "This is the exact disagreement that let the API path silently permit partial "
        "coverage while the domain contract required full service."
    )


def test_rg01_worker_payload_default_literal_is_false() -> None:
    """The worker's third default, read straight out of the parsed source.

    The literal in ``payload.get("allow_uncovered_demand", <default>)`` is the
    value a job or replay reconstructed from an empty payload actually solves
    under. It read True while the other two read False.
    """
    module = _parse(PUBSUB_WORKER_PY)
    func = _find_function(module, "_reconstruct_problem_from_payload")

    defaults: list[object] = []
    for node in ast.walk(func):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "allow_uncovered_demand"
        ):
            assert len(node.args) >= 2, (
                "payload.get('allow_uncovered_demand') has no explicit default; "
                "the reconstructed default is now implicit and unreviewable"
            )
            assert isinstance(node.args[1], ast.Constant), (
                "the allow_uncovered_demand default is no longer a literal, so the "
                "reconstructed behaviour cannot be read off the source"
            )
            defaults.append(node.args[1].value)

    assert defaults, (
        "_reconstruct_problem_from_payload no longer reads allow_uncovered_demand from "
        "the payload at all; the third definition site has moved or vanished"
    )
    assert all(d is False for d in defaults), (
        f"_reconstruct_problem_from_payload defaults allow_uncovered_demand to {defaults}. "
        "It must be False, matching OptimizationConstraints and the API request model."
    )


def test_rg01_worker_reconstruction_defaults_to_full_coverage() -> None:
    """The behavioural half: rebuild from an empty payload and read the problem."""
    from services.zonepilot.optimization.contracts import CapacityMode
    from services.zonepilot.optimization.pubsub_worker import _reconstruct_problem_from_payload

    try:
        problem = _reconstruct_problem_from_payload({})
    except FileNotFoundError as exc:  # pragma: no cover - artifact-dependent
        pytest.skip(f"R1 evidence artifacts unavailable: {exc}")

    assert problem.constraints.allow_uncovered_demand is False, (
        "A job reconstructed from an empty payload permits uncovered demand. This is the "
        "silent behaviour split: the operator asked for full service and the worker solved "
        "a different problem."
    )
    assert problem.constraints.capacity_mode is CapacityMode.NOT_MODELED


# --- RG-02: capacity_mode defaults to NOT_MODELED ----------------------------


def test_rg02_capacity_mode_defaults_to_not_modelled() -> None:
    from services.api.routers.observatory import OptimizationRequest
    from services.zonepilot.optimization.contracts import CapacityMode, OptimizationConstraints

    assert CapacityMode.NOT_MODELED.value == "NOT_MODELED"

    field = OptimizationConstraints.model_fields["capacity_mode"]
    assert field.default is CapacityMode.NOT_MODELED, (
        "OptimizationConstraints.capacity_mode no longer defaults to NOT_MODELED. "
        "An unmeasured throughput number would bind again by default."
    )

    built = OptimizationConstraints(
        min_open_facilities=1,
        max_open_facilities=2,
        max_travel_seconds=1800,
        minimum_coverage_basis_points=10_000,
    )
    assert built.capacity_mode is CapacityMode.NOT_MODELED
    assert OptimizationRequest().capacity_mode is CapacityMode.NOT_MODELED, (
        "The API request model would reinstate modelled capacity for every caller "
        "that does not name the mode explicitly."
    )


# --- RG-03: the flat capacity assumption must not bind by default ------------


def _tiny_problem(*, capacity_units: int = 10, capacity_mode=None):
    """A deliberately capacity-starved problem.

    Per-facility capacity is 10 units against 300 units of demand, so a modelled
    capacity constraint makes full coverage arithmetically impossible. Under the
    default NOT_MODELED mode it must still solve to a proved optimum.
    """
    from services.zonepilot.optimization.contracts import (
        DemandPoint,
        Facility,
        MatrixEvidenceClass,
        ObjectiveWeights,
        OptimizationConstraints,
        OptimizationProblem,
        SolverSettings,
        TravelMatrix,
        UncertaintyScenario,
    )

    facility_ids = ("F1", "F2")
    demand_ids = ("D1", "D2", "D3")
    matrix = TravelMatrix(
        matrix_id="matrix-guard",
        graph_version="guard-graph-1",
        router="guard-router",
        router_version="guard-router-1",
        evidence_class=MatrixEvidenceClass.TEST_ONLY,
        facility_ids=facility_ids,
        demand_ids=demand_ids,
        durations_seconds=((100, 200, 300), (300, 200, 100)),
    )
    constraint_kwargs = {} if capacity_mode is None else {"capacity_mode": capacity_mode}
    return OptimizationProblem(
        problem_id="problem-regression-guard",
        facilities=tuple(
            Facility(
                facility_id=facility_id,
                capacity_units=capacity_units,
                fixed_cost_units=1000,
                failure_exposure_basis_points=100,
            )
            for facility_id in facility_ids
        ),
        demand_points=tuple(DemandPoint(demand_id=d, demand_units=100) for d in demand_ids),
        scenarios=(
            UncertaintyScenario(
                scenario_id="s1",
                probability_basis_points=10_000,
                travel_matrix=matrix,
            ),
        ),
        constraints=OptimizationConstraints(
            min_open_facilities=1,
            max_open_facilities=2,
            max_travel_seconds=1800,
            minimum_coverage_basis_points=10_000,
            **constraint_kwargs,
        ),
        objective_weights=ObjectiveWeights(
            assumption_version="regression-guard-1",
            expected_travel=5000,
            p95_travel=1000,
            facility_cost=2000,
            failure_exposure=1000,
            coverage_loss=5000,
        ),
        solver_settings=SolverSettings(max_time_seconds=20.0),
    )


def test_rg03_flat_capacity_does_not_bind_by_default() -> None:
    from services.zonepilot.optimization import _cp_sat
    from services.zonepilot.optimization.contracts import OptimizationStatus

    result = _cp_sat.optimize_facilities(_tiny_problem())

    assert result.status is OptimizationStatus.OPTIMAL, (
        "A problem whose per-facility capacity is 30x below total demand failed to solve "
        f"under the DEFAULT capacity mode (status={result.status}). An invented throughput "
        "number is binding again and is making full service impossible."
    )
    assert result.fail_closed is False
    assert result.opened_facility_ids, "no facility was opened under the default mode"


def test_rg03_capacity_binds_only_when_explicitly_opted_in() -> None:
    """The other side of the guard: opting in must still model capacity.

    Without this, RG-03 could be 'satisfied' by deleting capacity modelling
    entirely, which would make the default indistinguishable from a no-op.
    """
    from services.zonepilot.optimization import _cp_sat
    from services.zonepilot.optimization.contracts import CapacityMode, OptimizationStatus

    result = _cp_sat.optimize_facilities(_tiny_problem(capacity_mode=CapacityMode.ASSUMPTION))

    assert result.status is OptimizationStatus.INFEASIBLE, (
        "CapacityMode.ASSUMPTION no longer posts a throughput constraint "
        f"(status={result.status}); the opt-in has become a no-op."
    )
    assert result.fail_closed is True


def test_rg03_capacity_constraint_is_guarded_by_capacity_mode() -> None:
    """The constraint must be reachable only through the CapacityMode test."""
    module = _parse(CP_SAT_PY)
    func = _find_function(module, "_build_model")

    guarded_capacity_ifs = [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.If)
        and "capacity_mode" in ast.dump(node.test)
        and "ASSUMPTION" in ast.dump(node.test)
    ]
    assert guarded_capacity_ifs, (
        "_build_model no longer gates anything on capacity_mode is CapacityMode.ASSUMPTION. "
        "Either the throughput constraint is unconditional again, or the guard moved."
    )

    capacity_uses = [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Attribute) and node.attr == "capacity_units"
    ]
    guarded_lines = {
        line
        for node in guarded_capacity_ifs
        for line in range(node.lineno, (node.end_lineno or node.lineno) + 1)
    }
    unguarded = [node.lineno for node in capacity_uses if node.lineno not in guarded_lines]
    assert not unguarded, (
        f"capacity_units is read outside the CapacityMode.ASSUMPTION guard at line(s) {unguarded} "
        "of _cp_sat.py. The unmeasured 1500-unit figure is entering the model by another route."
    )


# --- RG-04: the published objective is the one CP-SAT minimised --------------


def test_rg04_objective_contract_publishes_solver_fields() -> None:
    from services.zonepilot.optimization.contracts import ObjectiveBreakdown, ObjectiveComponent

    for field in ("solver_coefficient", "solver_scaled_contribution"):
        assert field in ObjectiveComponent.model_fields, (
            f"ObjectiveComponent.{field} has been removed; the authoritative solver "
            "arithmetic is no longer publishable and the display projection becomes "
            "the only number a reviewer can see."
        )
    assert "solver_objective_total" in ObjectiveBreakdown.model_fields, (
        "ObjectiveBreakdown.solver_objective_total has been removed."
    )
    # The display projection is retained, and must stay distinguishable from it.
    assert "weighted_total" in ObjectiveBreakdown.model_fields


def test_rg04_published_solver_total_is_the_value_cp_sat_minimised() -> None:
    """Rebuild the same model, solve it directly, and compare.

    This is the assertion that matters: the number the system publishes as the
    objective must be the number CP-SAT ranked solutions by, not the rounded
    human-facing projection that disagreed with it on every trial.
    """
    from ortools.sat.python import cp_model

    from services.zonepilot.optimization import _cp_sat

    problem = _tiny_problem()
    result = _cp_sat.optimize_facilities(problem)
    assert result.objective is not None

    state = _cp_sat._build_model(problem)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = problem.solver_settings.max_time_seconds
    solver.parameters.num_search_workers = problem.solver_settings.num_search_workers
    solver.parameters.random_seed = problem.solver_settings.random_seed
    status = solver.solve(state.model)
    assert status == cp_model.OPTIMAL, "the guard's own reference solve did not prove an optimum"

    cp_sat_objective = int(solver.objective_value)
    assert result.objective.solver_objective_total == cp_sat_objective, (
        f"published solver_objective_total={result.objective.solver_objective_total} but CP-SAT "
        f"minimised {cp_sat_objective}. The published objective is no longer the one the solver "
        "actually optimised."
    )
    assert result.objective.solver_objective_total == sum(
        component.solver_scaled_contribution for component in result.objective.components
    ), "the published total is not the sum of the published contributions; it cannot be reconciled"

    # The display projection is a different number. If these ever become equal by
    # construction, the projection has been substituted for the solver value.
    assert result.objective.weighted_total != result.objective.solver_objective_total, (
        "weighted_total now equals solver_objective_total. One of them has been "
        "redefined as the other, which is how the projection got mistaken for the objective."
    )


def test_rg04_solver_contribution_is_coefficient_times_raw_value() -> None:
    from services.zonepilot.optimization import _cp_sat

    result = _cp_sat.optimize_facilities(_tiny_problem())
    assert result.objective is not None
    assert result.objective.components, "the objective publishes no components"

    for component in result.objective.components:
        assert component.solver_scaled_contribution == component.solver_coefficient * component.raw_value, (
            f"component {component.name!r} does not reconcile: "
            f"{component.solver_scaled_contribution} != "
            f"{component.solver_coefficient} * {component.raw_value}"
        )


# --- RG-05: the policy version enters the problem fingerprint ----------------


def test_rg05_policy_version_is_carried_on_the_problem() -> None:
    from services.zonepilot.optimization.contracts import (
        OPTIMIZATION_POLICY_VERSION,
        OptimizationProblem,
    )

    assert OPTIMIZATION_POLICY_VERSION, "OPTIMIZATION_POLICY_VERSION is empty"
    assert re.fullmatch(r"\d+\.\d+\.\d+", OPTIMIZATION_POLICY_VERSION), (
        f"OPTIMIZATION_POLICY_VERSION={OPTIMIZATION_POLICY_VERSION!r} is not a semantic version"
    )
    assert "optimization_policy_version" in OptimizationProblem.model_fields, (
        "OptimizationProblem no longer carries optimization_policy_version, so a decision "
        "frozen under one set of mathematics can be replayed under another."
    )
    assert _tiny_problem().optimization_policy_version == OPTIMIZATION_POLICY_VERSION


def test_rg05_policy_version_enters_the_problem_fingerprint() -> None:
    from services.zonepilot.optimization.contracts import problem_fingerprint

    problem = _tiny_problem()
    baseline = problem_fingerprint(problem)
    shifted = problem_fingerprint(problem.model_copy(update={"optimization_policy_version": "9.9.9"}))

    assert baseline != shifted, (
        "changing optimization_policy_version does not change the problem fingerprint. "
        "The policy has fallen out of the hashed payload, so two different models share "
        "one lineage identity."
    )


# --- RG-06: replay compares the solver total, not the projection -------------


def _replay_objective_sources() -> list[tuple[int, str]]:
    """Every ``recomputed_obj = res.objective.<attr>`` in replay_decision, in order."""
    func = _find_function(_parse(LEDGER_PY), "replay_decision")
    sources: list[tuple[int, str]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "recomputed_obj" for t in node.targets):
            continue
        if isinstance(node.value, ast.Attribute):
            sources.append((node.lineno, node.value.attr))
    return sources


def test_rg06_replay_compares_the_solver_objective_total() -> None:
    sources = _replay_objective_sources()
    assert sources, (
        "replay_decision no longer assigns recomputed_obj from the result objective; "
        "the comparison this guard protects has moved or been deleted"
    )

    attrs = [attr for _, attr in sources]
    assert "solver_objective_total" in attrs, (
        f"replay_decision compares {attrs}, and none of them is solver_objective_total. "
        "Replay would verify against the human-facing projection, letting a decision "
        "'reproduce' against a number CP-SAT never ranked solutions by."
    )

    solver_line = min(line for line, attr in sources if attr == "solver_objective_total")
    projection_lines = [line for line, attr in sources if attr == "weighted_total"]
    for line in projection_lines:
        assert solver_line < line, (
            "weighted_total is preferred over solver_objective_total in replay_decision. "
            "The legacy projection may only be a fallback for records written before the "
            "solver total existed."
        )

    # The comparison itself must consume that variable.
    func = _find_function(_parse(LEDGER_PY), "replay_decision")
    obj_match_assigns = [
        node
        for node in ast.walk(func)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "obj_match" for t in node.targets)
    ]
    assert obj_match_assigns, "replay_decision no longer computes obj_match"
    assert any("recomputed_obj" in ast.dump(node.value) for node in obj_match_assigns), (
        "obj_match is no longer derived from recomputed_obj; the value this guard checks "
        "is computed and then discarded"
    )


def test_rg06_replay_refuses_a_foreign_policy_version() -> None:
    """A decision frozen under different mathematics must not be recomputed."""
    func = _find_function(_parse(LEDGER_PY), "replay_decision")
    statuses = {
        node.value.value
        for node in ast.walk(func)
        if isinstance(node, ast.keyword)
        and node.arg == "match_status"
        and isinstance(node.value, ast.Constant)
    }
    assert "LEGACY_POLICY_NOT_REPLAYABLE" in statuses, (
        "replay_decision no longer refuses a decision frozen under a different "
        f"OPTIMIZATION_POLICY_VERSION (statuses found: {sorted(statuses)}). Recomputing it "
        "would report two different models as drift."
    )
    assert any(
        isinstance(node, ast.Name) and node.id == "OPTIMIZATION_POLICY_VERSION"
        for node in ast.walk(func)
    ), "replay_decision no longer reads OPTIMIZATION_POLICY_VERSION at all"


# --- RG-07: decision class survives, and a manual decision has no policy -----


class _CapturingDecisionRepository:
    """Stands in for Postgres so the record itself can be inspected."""

    def __init__(self) -> None:
        self.saved: list[object] = []

    def record_decision(self, record, recorded_by=None):  # noqa: ANN001 - test double
        self.saved.append(record)
        return record


def _ledger_with_capture():
    from services.zonepilot.decisions.ledger import DecisionLedger

    repository = _CapturingDecisionRepository()
    ledger = DecisionLedger(
        code_sha="0" * 40,
        repository=repository,
        opt_repository=object(),
        assumption_registry=object(),
    )
    return ledger, repository


def _record_kwargs(**overrides):
    base = dict(
        workspace_id="ws-guard",
        decision_time=datetime.now(timezone.utc),
        network_version="net-1",
        dataset_version="ds-1",
        feature_snapshot_hash="fsh-1",
        selected_action="OPEN_FACILITIES",
        opened_facilities=["F1"],
        objective_value=None,
        expected_travel_seconds=None,
        p95_travel_seconds=None,
        coverage_basis_points=None,
        graph_version="graph-1",
        osrm_bundle_hash="bundle-1",
        solver_version="solver-1",
    )
    base.update(overrides)
    return base


def test_rg07_decision_record_carries_class_and_rationale() -> None:
    from services.zonepilot.decisions.contracts import DecisionRecord

    for field in ("decision_class", "operator_rationale"):
        assert field in DecisionRecord.model_fields, (
            f"DecisionRecord.{field} has been removed. An operator's declared "
            "MANUAL_OPERATOR_DECISION would again be validated by the API and discarded "
            "by the storage layer."
        )
    assert DecisionRecord.model_fields["decision_class"].default == "OPTIMIZER_DECISION"


def test_rg07_manual_decision_is_not_stamped_with_an_optimization_policy() -> None:
    ledger, repository = _ledger_with_capture()

    manual = ledger.record_decision(
        **_record_kwargs(
            decision_class="MANUAL_OPERATOR_DECISION",
            operator_rationale="Recorded by hand during the depot outage; no solver was run.",
        )
    )

    assert manual.decision_class == "MANUAL_OPERATOR_DECISION"
    assert manual.operator_rationale
    assert manual.optimization_policy_version is None, (
        "a hand-authored decision was stamped with optimization policy "
        f"{manual.optimization_policy_version!r}. It would then look replayable as though "
        "a solver had produced it."
    )
    assert repository.saved and repository.saved[0] is manual, (
        "record_decision did not hand the record to the repository; the declaration "
        "never reaches storage"
    )
    assert repository.saved[0].decision_class == "MANUAL_OPERATOR_DECISION"

    # An optimizer decision must still be stamped, or the guard would pass by
    # simply never recording a policy for anything.
    from services.zonepilot.optimization.contracts import OPTIMIZATION_POLICY_VERSION

    optimizer = ledger.record_decision(
        **_record_kwargs(
            objective_value=1,
            expected_travel_seconds=1,
            p95_travel_seconds=1,
            coverage_basis_points=1,
        )
    )
    assert optimizer.decision_class == "OPTIMIZER_DECISION"
    assert optimizer.optimization_policy_version == OPTIMIZATION_POLICY_VERSION, (
        "an optimizer decision is no longer stamped with the policy it was produced under"
    )

    # And nullability must not become a loophole for the optimizer path.
    with pytest.raises(ValueError, match="DECISION_LINEAGE_INCOMPLETE"):
        ledger.record_decision(**_record_kwargs())


def test_rg07_repository_persists_decision_class_and_rationale() -> None:
    """The original defect was storage-layer silence, so check the SQL too."""
    source = DECISION_REPO_PY.read_text(encoding="utf-8")
    for column in ("decision_class", "operator_rationale"):
        assert source.count(column) >= 2, (
            f"{column} appears fewer than twice in the decision repository. It must be "
            "both written and read back, or the declaration is dropped on the way to "
            "Postgres exactly as it was before."
        )

    module = _parse(DECISION_REPO_PY)
    written = {
        node.attr
        for node in ast.walk(module)
        if isinstance(node, ast.Attribute)
        and node.attr in {"decision_class", "operator_rationale"}
        and isinstance(node.value, ast.Name)
        and node.value.id == "decision"
    }
    assert written == {"decision_class", "operator_rationale"}, (
        f"the repository does not read both fields off the record (found {sorted(written)}); "
        "an unwritten column silently reverts to the OPTIMIZER_DECISION default"
    )


# --- RG-08: a forecast may say "no prediction yet" ---------------------------


def _prediction(**overrides):
    from services.zonepilot.forecast.contracts import (
        BaselineModelType,
        ForecastTarget,
        PredictionRecord,
    )

    now = datetime.now(timezone.utc)
    base = dict(
        prediction_id="pred-guard",
        workspace_id="ws-guard",
        zone_id="zone-guard",
        prediction_time=now,
        target_time=now,
        horizon_hours=1,
        target=ForecastTarget.HOURLY_PRECIPITATION_MM,
        baseline_model=BaselineModelType.LAST_OBSERVATION,
    )
    base.update(overrides)
    return PredictionRecord(**base)


def test_rg08_prediction_value_is_nullable_for_evidence_accumulating() -> None:
    from services.zonepilot.forecast.contracts import PredictionRecord

    field = PredictionRecord.model_fields["predicted_value"]
    assert field.default is None, (
        "PredictionRecord.predicted_value is no longer optional. The honest "
        "EVIDENCE_ACCUMULATING state becomes unrepresentable, which is what pressured "
        "the code into inventing forecast values."
    )

    empty = _prediction()
    assert empty.predicted_value is None
    # An empty prediction must claim no lineage either.
    assert empty.model_version is None
    assert empty.feature_snapshot_hash is None
    assert empty.dataset_version is None
    assert empty.graph_version is None


def test_rg08_prediction_with_a_value_requires_lineage() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="provenance"):
        _prediction(predicted_value=1.5)

    complete = _prediction(
        predicted_value=1.5,
        model_version="m-1",
        feature_snapshot_hash="fsh-1",
        dataset_version="ds-1",
        graph_version="graph-1",
    )
    assert complete.predicted_value == 1.5


def test_rg08_migration_drops_not_null_and_adds_the_lineage_check() -> None:
    assert FORECAST_MIGRATION.is_file(), (
        "the migration that made predicted_value nullable has been removed; every "
        "EVIDENCE_ACCUMULATING insert would fail and be reported as a store outage"
    )
    sql = " ".join(FORECAST_MIGRATION.read_text(encoding="utf-8").split()).lower()

    assert "alter column predicted_value drop not null" in sql, (
        "the migration no longer drops NOT NULL from predicted_value"
    )
    assert "forecast_prediction_requires_lineage" in sql, (
        "the CHECK that stops nullability becoming a way to store an unattributed "
        "number has been removed"
    )

    check_body = sql.split("forecast_prediction_requires_lineage check", 1)[-1]
    check_body = check_body.split(";", 1)[0]
    assert "predicted_value is null" in check_body
    for column in ("model_version is not null", "feature_dataset_version is not null", "graph_version is not null"):
        assert column in check_body, (
            f"the lineage CHECK no longer requires {column}; a prediction could be stored "
            "with no model behind it"
        )


# --- RG-09: no Andorra artifact under a Bengaluru name -----------------------

_GEO_REQUIRED_TESTS = (
    "test_pilot_roads_coordinates_are_actually_in_bengaluru",
    "test_no_artifact_named_bengaluru_contains_another_city",
    "test_no_city_named_routing_artifact_duplicates_another_city",
    "test_no_geographic_extract_is_actually_an_error_page",
)


def test_rg09_geo_lineage_suite_still_guards_the_andorra_defect() -> None:
    """The assertions live in tests/geo; this guards their continued existence.

    The original quarantine test only asserted that two hashes differed, which
    stayed green while the Andorra extract sat in the file named for Bengaluru.
    So it is not enough that these tests exist -- each must still contain real
    assert statements.
    """
    module = _parse(GEO_LINEAGE_PY)
    functions = {
        node.name: node
        for node in ast.walk(module)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    }

    missing = [name for name in _GEO_REQUIRED_TESTS if name not in functions]
    assert not missing, (
        f"tests/geo/test_pilot_roads_lineage.py no longer contains {missing}. "
        "The Andorra-as-Bengaluru regression coverage has been deleted."
    )

    for name in _GEO_REQUIRED_TESTS:
        asserts = [n for n in ast.walk(functions[name]) if isinstance(n, ast.Assert)]
        assert asserts, (
            f"{name} contains no assert statement. It would report green while asserting "
            "nothing, which is exactly how the wrong country shipped."
        )


# --- RG-10: typed 503 on store outage, and no reserved log attributes --------


class _BrokenRateLimitStore:
    def increment(self, keys, windows):  # noqa: ANN001 - test double
        from services.api.core.ratelimit import StoreUnavailable

        raise StoreUnavailable("simulated rate limit store outage")

    def prune(self, batch_size):  # noqa: ANN001 - test double
        return 0

    def active_optimization_jobs(self, workspace_id):  # noqa: ANN001 - test double
        return 0


def _client_with_broken_store(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from services.api.core import ratelimit
    from services.api.core.middleware import RequestIdMiddleware

    monkeypatch.setenv("ZONEPILOT_RATE_LIMIT_ENABLED", "true")
    monkeypatch.delenv("ZONEPILOT_RATE_LIMIT_FAIL_OPEN", raising=False)
    monkeypatch.setattr(ratelimit.limiter, "_store", _BrokenRateLimitStore(), raising=False)

    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/api/v1/guard/zones")
    def _zones():
        return {"served": True}

    return TestClient(app)


def test_rg10_store_outage_returns_typed_503(monkeypatch) -> None:
    """Exercises the real handler, log call included.

    The defect was a KeyError raised INSIDE this branch by a reserved LogRecord
    attribute in ``extra``, which turned the correct 503 into an opaque 500. A
    real request through the middleware is the only assertion that catches that,
    because the limiter's decision was never the broken part.
    """
    response = _client_with_broken_store(monkeypatch).get("/api/v1/guard/zones")

    assert response.status_code == 503, (
        f"a rate limit store outage returned {response.status_code}, not 503. "
        "500 means the outage handler itself is raising (the reserved-LogRecord-attribute "
        "defect); 200 means the limiter failed open and served unmetered."
    )
    body = response.json()
    assert body["error"]["code"] == "DEPENDENCY_UNAVAILABLE", (
        f"the outage is typed as {body['error']['code']!r}; F-025 maps a dependency outage "
        "to DEPENDENCY_UNAVAILABLE so the caller can tell it is retryable"
    )
    assert body["error"]["retryable"] is True
    assert body["error"]["details"]["subsystem"] == "rate_limit_store"
    assert int(response.headers["retry-after"]) >= 1


def test_rg10_store_outage_does_not_fail_open(monkeypatch) -> None:
    """The route must not be served. Failing open only moves the failure later."""
    response = _client_with_broken_store(monkeypatch).get("/api/v1/guard/zones")

    assert response.status_code != 200, (
        "the request was served while the rate limit store was down. Reads used to fail "
        "open here, which sounded like graceful degradation and was not: the store IS the "
        "Postgres the read route depends on."
    )
    body = response.json()
    assert "served" not in body, "the route handler ran despite the limiter being unable to count"
    assert "error" in body


_RESERVED_LOGRECORD_ATTRS = frozenset(
    {
        "message",
        "asctime",
        "args",
        "exc_info",
        "levelname",
        "module",
        "name",
        "pathname",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "thread",
        "process",
    }
)

_LOG_METHODS = frozenset({"debug", "info", "warning", "warn", "error", "exception", "critical", "log"})

_SCAN_SKIP_DIRS = frozenset(
    {
        ".git",
        ".next",
        ".venv",
        "__pycache__",
        "node_modules",
        "venv",
        "zonepilot.egg-info",
        "legacy_demo",
    }
)


def _python_sources() -> list[Path]:
    return [
        path
        for path in REPO_ROOT.rglob("*.py")
        if not _SCAN_SKIP_DIRS & set(path.relative_to(REPO_ROOT).parts)
    ]


def test_rg10_no_logging_call_uses_a_reserved_logrecord_attribute_in_extra() -> None:
    """Repository-wide. A reserved key in ``extra`` raises inside logging itself.

    ``logging`` merges ``extra`` onto the LogRecord and refuses to overwrite its
    own attributes with a KeyError. The failure therefore lands in whatever code
    path was being logged -- typically an error handler, which is where logging
    happens most -- and converts a correct typed response into a 500.
    """
    sources = _python_sources()
    assert len(sources) > 100, (
        f"only {len(sources)} python files were scanned; the scan root or skip list is wrong "
        "and this guard would pass by looking at almost nothing"
    )

    violations: list[str] = []
    for path in sources:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if called not in _LOG_METHODS:
                continue
            for keyword in node.keywords:
                if keyword.arg != "extra" or not isinstance(keyword.value, ast.Dict):
                    continue
                for key in keyword.value.keys:
                    if isinstance(key, ast.Constant) and key.value in _RESERVED_LOGRECORD_ATTRS:
                        violations.append(
                            f"{path.relative_to(REPO_ROOT).as_posix()}:{node.lineno} "
                            f"extra={{{key.value!r}: ...}}"
                        )

    assert not violations, (
        "logging call(s) pass a reserved LogRecord attribute inside extra={...}. "
        "logging raises KeyError at the call site, so the enclosing request fails with an "
        "opaque 500 instead of its intended response:\n  " + "\n  ".join(violations)
    )


# --- the guard's own sanity check -------------------------------------------


def test_environment_is_the_repository_under_test() -> None:
    """Cheap protection against the suite silently testing an installed copy."""
    import services.zonepilot.optimization.contracts as contracts_module

    loaded = Path(contracts_module.__file__).resolve()
    assert loaded == CONTRACTS_PY.resolve(), (
        f"the guard imported {loaded}, not {CONTRACTS_PY}. It would be asserting against "
        "a different checkout than the one being merged."
    )
    assert os.environ.get("ZONEPILOT_DATA_ROOT") is None or Path(
        os.environ["ZONEPILOT_DATA_ROOT"]
    ).exists()
