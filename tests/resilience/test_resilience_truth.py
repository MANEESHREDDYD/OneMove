"""F-010 (reopened): the resilience path must not invent what it did not measure.

Three defects are gated here.

1. **Orphan persistence.** The service wrote the scenario row before resolving
   the authentic travel matrix, so a ``MATRIX_UNAVAILABLE`` failure left a
   scenario in PostgreSQL with no evaluation behind it. A request that produced
   no result must leave no trace of having run.
2. **Invented operational metrics.** The engine hardcoded demand, zone,
   capacity, disconnection, redundancy and open-facility counts, so coverage was
   always full, capacity loss always none and disconnected zones always none --
   and those figures were persisted as if measured. Every metric must now be
   derived from the frozen authentic matrix and the scenario, or reported
   UNAVAILABLE with a reason. Zero is a measurement, never a stand-in.
3. **Invented provenance.** The engine pinned ``code_sha`` to a literal and
   hashed it into every ``evaluation_id``.

None of these tests need a database. The persistence assertions use a recording
double, and the one test that exercises the real repository relies on validation
happening before a connection is ever opened.
"""

from __future__ import annotations

import ast
import inspect
import re
import textwrap
from pathlib import Path
from typing import Any

import pytest

from services.temporal.contracts import EvidenceClass
from services.zonepilot.optimization.contracts import MatrixEvidenceClass, TravelMatrix
from services.zonepilot.release import current_release_sha
from services.zonepilot.resilience import derivation
from services.zonepilot.resilience import engine as engine_module
from services.zonepilot.resilience import repository as repository_module
from services.zonepilot.resilience import service as resilience_service
from services.zonepilot.resilience.contracts import (
    METRIC_FIELDS,
    FrozenScenarioInputs,
    MetricUnavailable,
    ResilienceMetrics,
    ResilienceScenario,
    ScenarioDisruption,
    ScenarioType,
)
from services.zonepilot.resilience.derivation import (
    ScenarioNotRepresentable,
    build_frozen_inputs,
    derive_counts,
)
from services.zonepilot.resilience.engine import ResilienceEngine, metrics_from_counts
from services.zonepilot.resilience.repository import (
    IncompleteEvaluationError,
    ResilienceRepository,
)
from services.zonepilot.resilience.service import ResilienceService, UnknownScenarioType

REPO_ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------- #
# Fixtures: a small authentic-shaped matrix, no database, no artifacts.
# --------------------------------------------------------------------------- #


def _matrix(
    *,
    facilities: int = 3,
    demands: int = 4,
    evidence: MatrixEvidenceClass = MatrixEvidenceClass.PUBLIC_GEOGRAPHIC,
) -> TravelMatrix:
    """A routed matrix whose durations differ per cell, so constants show up."""
    durations = tuple(
        tuple(300 + 200 * facility + 100 * demand for demand in range(demands)) for facility in range(facilities)
    )
    return TravelMatrix(
        matrix_id="matrix-test-r4",
        graph_version="1.1.0+test",
        router="osrm-routed-table",
        router_version="1.0.0",
        evidence_class=evidence,
        facility_ids=tuple(f"fac:{index}" for index in range(facilities)),
        demand_ids=tuple(f"zone:{index}" for index in range(demands)),
        durations_seconds=durations,
    )


def _scenario(scenario_type: ScenarioType = ScenarioType.FACILITY_OUTAGE, **params: Any) -> ResilienceScenario:
    return ResilienceScenario(
        scenario_id="scen-test",
        scenario_type=scenario_type,
        description="test scenario",
        parameters=dict(params),
        graph_version="1.1",
    )


class RecordingRepository:
    """Records every write attempt. Any call at all is a persistence event."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def save_evaluation(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("save_evaluation", kwargs))
        return {"scenario_id": kwargs["scenario_id"]}

    def save_result(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("save_result", kwargs))
        return {}

    def get_scenario(self, scenario_id: str, workspace_id: str | None = None) -> dict[str, Any]:
        return {"scenario_id": scenario_id, "workspace_id": workspace_id}

    def list_scenarios(self, workspace_id: str) -> list[dict[str, Any]]:
        return []


@pytest.fixture()
def recorder() -> RecordingRepository:
    return RecordingRepository()


# --------------------------------------------------------------------------- #
# DEFECT 1 -- nothing is persisted before the authentic matrix is resolved.
# --------------------------------------------------------------------------- #


def test_missing_matrix_persists_nothing_at_all(tmp_path, monkeypatch, recorder) -> None:
    """MATRIX_UNAVAILABLE must not leave an orphan scenario row behind."""
    monkeypatch.setattr(resilience_service, "default_data_root", lambda: tmp_path)
    service = ResilienceService(repository=recorder)

    with pytest.raises(FileNotFoundError) as exc:
        service.execute_scenario(
            workspace_id="ws-1",
            scenario_type="FACILITY_OUTAGE",
            parameters={"disabled_facility_ids": ["fac:0"]},
        )

    assert "MATRIX_UNAVAILABLE" in str(exc.value)
    assert recorder.calls == [], f"a failed run persisted {[name for name, _ in recorder.calls]}"


def test_matrix_is_resolved_before_any_write_in_source_order() -> None:
    """Static guard: no repository write may precede the matrix resolution."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(ResilienceService.execute_scenario)))

    write_lines: list[int] = []
    matrix_lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.startswith("save_"):
            write_lines.append(node.lineno)
        if isinstance(node, ast.Name) and node.id in {"_authentic_baseline_matrix", "build_frozen_inputs"}:
            matrix_lines.append(node.lineno)

    assert write_lines, "execute_scenario no longer persists anything; the guard needs updating"
    assert matrix_lines, "execute_scenario no longer resolves the authentic matrix"
    assert min(write_lines) > max(matrix_lines), (
        "a repository write appears before the authentic matrix and frozen inputs are resolved; "
        "that ordering is what produced orphan scenario rows"
    )


def test_unrepresentable_scenario_persists_nothing(recorder) -> None:
    """An unmodelled disruption is refused, not evaluated against a clean matrix."""
    service = ResilienceService(repository=recorder)

    with pytest.raises(ScenarioNotRepresentable) as exc:
        service.execute_scenario(
            workspace_id="ws-1",
            scenario_type="ROAD_CLOSURE",
            parameters={"closed_roads": ["way:101", "way:102"]},
            baseline_matrix=_matrix(),
        )

    assert "closed_roads" in str(exc.value)
    assert recorder.calls == []


def test_scenario_declaring_no_effect_is_refused(recorder) -> None:
    """An empty parameter set would grade the baseline as though it were a failure."""
    service = ResilienceService(repository=recorder)

    with pytest.raises(ScenarioNotRepresentable):
        service.execute_scenario(
            workspace_id="ws-1",
            scenario_type="CONGESTION_SPIKE",
            parameters={},
            baseline_matrix=_matrix(),
        )
    assert recorder.calls == []


def test_unknown_scenario_type_is_refused_not_silently_rewritten(recorder) -> None:
    service = ResilienceService(repository=recorder)

    with pytest.raises(UnknownScenarioType):
        service.execute_scenario(
            workspace_id="ws-1",
            scenario_type="METEOR_STRIKE",
            parameters={"disabled_facility_ids": ["fac:0"]},
            baseline_matrix=_matrix(),
        )
    assert recorder.calls == []


def test_successful_run_persists_scenario_and_evaluation_together(recorder) -> None:
    """One atomic write, carrying the metrics object rather than loose integers."""
    service = ResilienceService(repository=recorder)
    stored = service.execute_scenario(
        workspace_id="ws-1",
        scenario_type="CONGESTION_SPIKE",
        parameters={"travel_time_inflation_basis_points": 2_000},
        baseline_matrix=_matrix(),
    )

    assert [name for name, _ in recorder.calls] == ["save_evaluation"]
    _, kwargs = recorder.calls[0]
    assert isinstance(kwargs["metrics"], ResilienceMetrics)
    assert kwargs["evaluation_id"].startswith("eval-")
    assert kwargs["code_sha"] == current_release_sha()
    # Provenance travels with the response, not just the row.
    assert stored["derivation"]["matrix_evidence_class"] == "PUBLIC_GEOGRAPHIC"
    assert stored["derivation"]["disruption_evidence_class"] == "SIMULATED"
    assert stored["metrics_evidence_class"] == "DERIVED"


def test_repository_refuses_incomplete_evaluations_before_connecting() -> None:
    """resilience_results has no NULL column for UNAVAILABLE; refuse, do not zero-fill.

    The DSN points nowhere. If validation happened after connecting, this would
    raise a connection error instead.
    """
    repo = ResilienceRepository(dsn="postgresql://unused:unused@127.0.0.1:1/none")
    incomplete = ResilienceMetrics(
        coverage_basis_points=10_000,
        p50_duration_seconds=1,
        p90_duration_seconds=2,
        p95_duration_seconds=3,
        disconnected_zones_count=0,
        redundancy_index_basis_points=5_000,
        unavailable=(
            MetricUnavailable(metric="failure_exposure_score", reason="capacity unavailable"),
            MetricUnavailable(metric="capacity_loss_basis_points", reason="no capacity assumption"),
        ),
    )

    with pytest.raises(IncompleteEvaluationError) as exc:
        repo.save_evaluation(
            scenario_id="scen-1",
            workspace_id="ws-1",
            scenario_type="FACILITY_OUTAGE",
            description="d",
            parameters={},
            seed=42,
            graph_version="1.1",
            created_by=None,
            evaluation_id="eval-1",
            metrics=incomplete,
            degradation_grade="ROBUST",
            code_sha=current_release_sha(),
        )
    assert "METRICS_UNAVAILABLE" in str(exc.value)
    assert "capacity_loss_basis_points" in str(exc.value)


def test_result_insert_columns_match_metric_field_order() -> None:
    """The INSERT binds metrics positionally; a reordering would silently swap them."""
    sql = repository_module.ResilienceRepository._result_insert()
    columns = sql[: sql.index("VALUES")]
    listed = [name.strip() for name in re.sub(r".*\(", "", columns, count=1).replace(")", "").split(",")]
    start = listed.index(METRIC_FIELDS[0])
    assert tuple(listed[start : start + len(METRIC_FIELDS)]) == METRIC_FIELDS


def test_persistence_lineage_has_no_defaults() -> None:
    for method in (ResilienceRepository.save_evaluation, ResilienceRepository.save_result):
        param = inspect.signature(method).parameters["code_sha"]
        assert param.default is inspect.Parameter.empty, f"{method.__name__} must not default code_sha"


# --------------------------------------------------------------------------- #
# DEFECT 2 -- no invented operational constant survives.
# --------------------------------------------------------------------------- #


def _code_constants(module) -> list[Any]:
    """Integer literals in real code, ignoring docstrings and comments."""
    tree = ast.parse(inspect.getsource(module))
    values: list[Any] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            values.append(node.value)
    return values


def test_engine_source_contains_no_fabricated_operational_constants() -> None:
    """The specific invented figures must be absent from the engine entirely."""
    source = inspect.getsource(engine_module)
    for forbidden in (
        "total_demands=94",
        "covered_demands=94",
        "total_capacity=1200",
        "lost_capacity=0",
        "zone_count=94",
        "disconnected_count=0",
        "redundant_facility_count=2",
        "total_open_facilities=4",
    ):
        assert forbidden not in source, f"engine still hardcodes {forbidden}"

    constants = _code_constants(engine_module)
    for number in (94, 1_200):
        assert number not in constants, f"engine still carries the literal {number}"


def test_engine_takes_no_operational_defaults() -> None:
    """Every operational count must be supplied by the derivation, never defaulted."""
    operational = {
        "total_demands",
        "covered_demands",
        "total_capacity",
        "lost_capacity",
        "zone_count",
        "disconnected_count",
        "redundant_facility_count",
        "total_open_facilities",
    }
    for func in (ResilienceEngine.evaluate_scenario, engine_module.compute_metrics):
        for name, param in inspect.signature(func).parameters.items():
            if name in operational:
                assert param.default is inspect.Parameter.empty, (
                    f"{func.__name__} defaults {name}; an unsupplied operational count must fail, not assume"
                )


def test_evaluate_scenario_rejects_a_bare_duration_sequence() -> None:
    """Durations alone carry no provenance and cannot support derived metrics."""
    with pytest.raises(TypeError):
        ResilienceEngine().evaluate_scenario(_scenario(), [400, 500, 650])  # type: ignore[arg-type]


def test_counts_are_derived_from_the_matrix_axes_not_constants() -> None:
    """Change the matrix, and the counts change with it."""
    small = derive_counts(
        build_frozen_inputs(
            _matrix(facilities=3, demands=4),
            scenario_type=ScenarioType.CONGESTION_SPIKE,
            parameters={"travel_time_inflation_basis_points": 1_000},
        )
    )
    large = derive_counts(
        build_frozen_inputs(
            _matrix(facilities=5, demands=9),
            scenario_type=ScenarioType.CONGESTION_SPIKE,
            parameters={"travel_time_inflation_basis_points": 1_000},
        )
    )
    assert (small.total_demands, small.zone_count, small.total_open_facilities) == (4, 4, 3)
    assert (large.total_demands, large.zone_count, large.total_open_facilities) == (9, 9, 5)


def test_disconnected_zones_are_measured_not_assumed_zero() -> None:
    """Disabling every facility disconnects every zone; the count must say so."""
    matrix = _matrix(facilities=3, demands=4)
    inputs = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.FACILITY_OUTAGE,
        parameters={"disabled_facility_ids": list(matrix.facility_ids)},
    )
    counts = derive_counts(inputs)
    assert counts.disconnected_count == 4
    assert counts.total_open_facilities == 0

    metrics = metrics_from_counts(counts)
    assert metrics.disconnected_zones_count == 4
    assert metrics.coverage_basis_points == 0  # measured: nothing is reachable
    # No zone is routable, so there is no travel-time distribution to quantise.
    assert metrics.p95_duration_seconds is None
    assert "p95_duration_seconds" in metrics.unavailable_reasons()


def test_a_single_closed_pair_changes_reachability() -> None:
    """Per-pair closures are applied, so disconnection is not a constant."""
    matrix = _matrix(facilities=2, demands=2)
    inputs = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.ROAD_CLOSURE,
        parameters={
            "unreachable_facility_demand_pairs": [
                [matrix.facility_ids[0], matrix.demand_ids[0]],
                [matrix.facility_ids[1], matrix.demand_ids[0]],
            ]
        },
    )
    counts = derive_counts(inputs)
    assert counts.disconnected_count == 1
    assert counts.total_demands == 2


def test_coverage_follows_the_declared_threshold() -> None:
    """Coverage is derived from the matrix against a named, frozen definition."""
    matrix = _matrix(facilities=2, demands=3)  # nearest durations: 300, 400, 500
    generous = derive_counts(
        build_frozen_inputs(
            matrix,
            scenario_type=ScenarioType.CONGESTION_SPIKE,
            parameters={"travel_time_inflation_basis_points": 1},
        )
    )
    strict = derive_counts(
        build_frozen_inputs(
            matrix,
            scenario_type=ScenarioType.CONGESTION_SPIKE,
            parameters={
                "travel_time_inflation_basis_points": 1,
                "coverage_max_travel_seconds": 350,
                "coverage_assumption_source": "test-declared threshold",
            },
        )
    )
    assert generous.covered_demands == 3
    assert strict.covered_demands == 1
    assert metrics_from_counts(strict).coverage_basis_points == 3_333


def test_travel_inflation_actually_moves_the_quantiles() -> None:
    matrix = _matrix(facilities=2, demands=4)
    clean = metrics_from_counts(
        derive_counts(
            build_frozen_inputs(
                matrix,
                scenario_type=ScenarioType.CONGESTION_SPIKE,
                parameters={"travel_time_inflation_basis_points": 1},
            )
        )
    )
    stressed = metrics_from_counts(
        derive_counts(
            build_frozen_inputs(
                matrix,
                scenario_type=ScenarioType.CONGESTION_SPIKE,
                parameters={"travel_time_inflation_basis_points": 5_000},
            )
        )
    )
    assert stressed.p95_duration_seconds > clean.p95_duration_seconds  # type: ignore[operator]


def test_redundancy_is_derived_from_what_each_facility_uniquely_covers() -> None:
    """One facility covering everything alone is not redundant."""
    matrix = TravelMatrix(
        matrix_id="matrix-test-r4",
        graph_version="1.1.0+test",
        router="osrm-routed-table",
        router_version="1.0.0",
        evidence_class=MatrixEvidenceClass.PUBLIC_GEOGRAPHIC,
        facility_ids=("fac:near", "fac:far"),
        demand_ids=("zone:0",),
        # Only fac:near is inside the 1800s declared threshold.
        durations_seconds=((600,), (3_000,)),
    )
    counts = derive_counts(
        build_frozen_inputs(
            matrix,
            scenario_type=ScenarioType.CONGESTION_SPIKE,
            parameters={"travel_time_inflation_basis_points": 1},
        )
    )
    assert counts.total_open_facilities == 2
    assert counts.redundant_facility_count == 1  # fac:far adds nothing; fac:near is the sole cover
    assert metrics_from_counts(counts).redundancy_index_basis_points == 5_000


# --------------------------------------------------------------------------- #
# DEFECT 2 -- capacity has no source, so it is UNAVAILABLE rather than invented.
# --------------------------------------------------------------------------- #


def test_capacity_loss_is_unavailable_without_a_frozen_capacity_assumption() -> None:
    matrix = _matrix()
    counts = derive_counts(
        build_frozen_inputs(
            matrix,
            scenario_type=ScenarioType.FACILITY_OUTAGE,
            parameters={"disabled_facility_ids": [matrix.facility_ids[0]]},
        )
    )
    metrics = metrics_from_counts(counts)

    assert metrics.capacity_loss_basis_points is None
    reasons = metrics.unavailable_reasons()
    assert "capacity" in reasons["capacity_loss_basis_points"]
    # The composite that weights capacity is unavailable too, not recomputed on half its inputs.
    assert metrics.failure_exposure_score is None
    assert "capacity" in reasons["failure_exposure_score"]


def test_capacity_loss_is_derived_when_an_assumption_is_frozen() -> None:
    matrix = _matrix(facilities=4, demands=2)
    inputs = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.FACILITY_OUTAGE,
        parameters={
            "disabled_facility_ids": [matrix.facility_ids[0]],
            "facility_capacity_units": {facility_id: 100 for facility_id in matrix.facility_ids},
            "capacity_assumption_source": "test ledger, declared as an assumption",
        },
    )
    assert inputs.capacity_assumption is not None
    assert inputs.capacity_assumption.evidence_class is EvidenceClass.ASSUMPTION

    metrics = metrics_from_counts(derive_counts(inputs))
    assert metrics.capacity_loss_basis_points == 2_500  # 100 of 400 units
    assert metrics.is_complete


def test_capacity_assumption_requires_a_named_source() -> None:
    matrix = _matrix()
    with pytest.raises(ScenarioNotRepresentable):
        build_frozen_inputs(
            matrix,
            scenario_type=ScenarioType.FACILITY_OUTAGE,
            parameters={
                "disabled_facility_ids": [matrix.facility_ids[0]],
                "facility_capacity_units": {facility_id: 100 for facility_id in matrix.facility_ids},
            },
        )


def test_zero_capacity_loss_is_only_reported_when_nothing_was_removed() -> None:
    """The single legitimate zero: a scenario that takes no capacity away."""
    matrix = _matrix()
    counts = derive_counts(
        build_frozen_inputs(
            matrix,
            scenario_type=ScenarioType.CONGESTION_SPIKE,
            parameters={"travel_time_inflation_basis_points": 3_000},
        )
    )
    assert counts.lost_capacity == 0
    assert counts.total_capacity is None  # still unknown, and still not needed
    assert metrics_from_counts(counts).capacity_loss_basis_points == 0


def test_partial_capacity_ledger_is_unavailable_not_partially_totalled() -> None:
    matrix = _matrix(facilities=3, demands=2)
    inputs = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.FACILITY_OUTAGE,
        parameters={
            "disabled_facility_ids": [matrix.facility_ids[0]],
            "facility_capacity_units": {matrix.facility_ids[0]: 100},
            "capacity_assumption_source": "deliberately incomplete ledger",
        },
    )
    metrics = metrics_from_counts(derive_counts(inputs))
    assert metrics.capacity_loss_basis_points is None
    assert "omits" in metrics.unavailable_reasons()["capacity_loss_basis_points"]


# --------------------------------------------------------------------------- #
# Every metric is derived or explicitly unavailable -- never silently zero.
# --------------------------------------------------------------------------- #


def test_an_uncomputed_metric_must_declare_why() -> None:
    with pytest.raises(ValueError, match="must declare why it is unavailable"):
        ResilienceMetrics(
            coverage_basis_points=None,
            p50_duration_seconds=1,
            p90_duration_seconds=2,
            p95_duration_seconds=3,
            disconnected_zones_count=0,
            redundancy_index_basis_points=0,
            failure_exposure_score=0,
            capacity_loss_basis_points=0,
        )


def test_a_metric_cannot_be_both_derived_and_unavailable() -> None:
    with pytest.raises(ValueError, match="cannot be both derived and unavailable"):
        ResilienceMetrics(
            coverage_basis_points=10_000,
            p50_duration_seconds=1,
            p90_duration_seconds=2,
            p95_duration_seconds=3,
            disconnected_zones_count=0,
            redundancy_index_basis_points=0,
            failure_exposure_score=0,
            capacity_loss_basis_points=0,
            unavailable=(MetricUnavailable(metric="coverage_basis_points", reason="contradiction"),),
        )


def test_unavailable_entries_must_name_a_real_metric() -> None:
    with pytest.raises(ValueError, match="unknown resilience metric"):
        MetricUnavailable(metric="made_up_metric", reason="nope")


def test_every_metric_field_is_covered_by_the_invariant() -> None:
    """METRIC_FIELDS must stay in step with the model, or gaps go unchecked."""
    model_fields = set(ResilienceMetrics.model_fields) - {"unavailable", "evidence_class"}
    assert model_fields == set(METRIC_FIELDS)


def test_grade_is_declined_when_its_inputs_are_unavailable() -> None:
    metrics = ResilienceMetrics(
        disconnected_zones_count=0,
        unavailable=tuple(
            MetricUnavailable(metric=field, reason="not derivable in this test")
            for field in METRIC_FIELDS
            if field != "disconnected_zones_count"
        ),
    )
    assert resilience_service._compute_grade(metrics) == "UNAVAILABLE"


# --------------------------------------------------------------------------- #
# DEFECT 3 -- code_sha is the running release, not a literal.
# --------------------------------------------------------------------------- #


def test_code_sha_is_not_a_literal_anywhere_in_the_resilience_package() -> None:
    sha_literal = re.compile(r"[0-9a-f]{40}")
    for module in (engine_module, resilience_service, repository_module, derivation):
        source = inspect.getsource(module)
        found = sha_literal.findall(source)
        assert not found, f"{module.__name__} carries a hardcoded 40-hex sha: {found}"


def test_engine_defaults_code_sha_to_the_running_release() -> None:
    assert inspect.signature(ResilienceEngine.__init__).parameters["code_sha"].default is None
    assert ResilienceEngine().code_sha == current_release_sha()
    assert re.fullmatch(r"[0-9a-f]{40}", ResilienceEngine().code_sha)


def test_release_sha_tracks_the_deployed_commit(monkeypatch) -> None:
    """The SHA comes from the deployment environment, not from source."""
    override = "a" * 40
    monkeypatch.setenv("ZONEPILOT_GIT_SHA", override)
    assert ResilienceEngine().code_sha == override


def test_evaluation_id_is_bound_to_the_build_and_the_inputs() -> None:
    matrix = _matrix()
    inputs = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.CONGESTION_SPIKE,
        parameters={"travel_time_inflation_basis_points": 1_000},
    )
    other_inputs = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.CONGESTION_SPIKE,
        parameters={"travel_time_inflation_basis_points": 2_000},
    )
    scenario = _scenario(ScenarioType.CONGESTION_SPIKE, travel_time_inflation_basis_points=1_000)

    build_a = ResilienceEngine(code_sha="a" * 40).evaluate_scenario(scenario, inputs)
    build_b = ResilienceEngine(code_sha="b" * 40).evaluate_scenario(scenario, inputs)
    other = ResilienceEngine(code_sha="a" * 40).evaluate_scenario(scenario, other_inputs)

    assert build_a.evaluation_id != build_b.evaluation_id, "evaluation_id ignores the build it came from"
    assert build_a.evaluation_id != other.evaluation_id, "evaluation_id ignores the inputs it was derived from"


def test_engine_refuses_a_blank_code_sha() -> None:
    with pytest.raises(ValueError, match="code_sha"):
        ResilienceEngine(code_sha="   ")


# --------------------------------------------------------------------------- #
# Evidence classes are truthful.
# --------------------------------------------------------------------------- #


def test_routing_baseline_may_not_claim_simulated_evidence() -> None:
    with pytest.raises(ValueError, match="cannot claim evidence_class"):
        FrozenScenarioInputs(
            matrix_id="m",
            graph_version="1.1",
            router="osrm-routed-table",
            router_version="1.0.0",
            matrix_evidence_class=EvidenceClass.SIMULATED,
            facility_ids=("fac:0",),
            demand_ids=("zone:0",),
            baseline_durations_seconds=((300,),),
            disruption=ScenarioDisruption(disabled_facility_ids=("fac:0",)),
            inputs_sha256="0" * 64,
        )


def test_evidence_classes_are_separated_end_to_end() -> None:
    inputs = build_frozen_inputs(
        _matrix(),
        scenario_type=ScenarioType.CONGESTION_SPIKE,
        parameters={"travel_time_inflation_basis_points": 1_000},
    )
    result = ResilienceEngine().evaluate_scenario(
        _scenario(ScenarioType.CONGESTION_SPIKE, travel_time_inflation_basis_points=1_000),
        inputs,
    )

    assert inputs.matrix_evidence_class is EvidenceClass.PUBLIC_GEOGRAPHIC  # authentic routing base
    assert inputs.disruption.evidence_class is EvidenceClass.SIMULATED  # counterfactual
    assert inputs.coverage_assumption.evidence_class is EvidenceClass.ASSUMPTION  # declared definition
    assert result.metrics.evidence_class is EvidenceClass.DERIVED  # computed from the above
    assert result.scenario.evidence_class is EvidenceClass.SIMULATED


def test_frozen_inputs_digest_covers_the_disruption_and_the_assumptions() -> None:
    matrix = _matrix()
    base = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.CONGESTION_SPIKE,
        parameters={"travel_time_inflation_basis_points": 1_000},
    )
    changed_threshold = build_frozen_inputs(
        matrix,
        scenario_type=ScenarioType.CONGESTION_SPIKE,
        parameters={
            "travel_time_inflation_basis_points": 1_000,
            "coverage_max_travel_seconds": 900,
            "coverage_assumption_source": "test-declared threshold",
        },
    )
    assert base.inputs_sha256 != changed_threshold.inputs_sha256
    assert re.fullmatch(r"[0-9a-f]{64}", base.inputs_sha256)


def test_no_synthetic_matrix_generator_returned() -> None:
    """F-010's original fabrication must not creep back into the package."""
    for module in (resilience_service, derivation, engine_module):
        source = inspect.getsource(module)
        assert "% 600" not in source, f"{module.__name__} synthesises durations from index arithmetic"


def test_resilience_package_draws_no_random_values() -> None:
    """A resilience metric must be reproducible from its frozen inputs."""
    package = REPO_ROOT / "services" / "zonepilot" / "resilience"
    for path in sorted(package.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "import random" not in text, f"{path.name} draws random values into a resilience result"
