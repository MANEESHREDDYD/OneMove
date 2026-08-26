"""Core R4 Network Resilience evaluation engine.

F-010 (reopened) removed the last two fabrications from this file:

* ``evaluate_scenario`` carried default operational constants for the demand,
  zone, capacity, disconnection, redundancy and open-facility counts, and no
  caller ever overrode them. Coverage was therefore pinned at full, capacity
  loss at none and disconnected zones at none, and those figures were written
  to PostgreSQL as if they had been measured. The engine now takes
  :class:`FrozenScenarioInputs` and derives every count from the authentic
  matrix and the simulated disruption. No operational count may be a literal in
  this module; ``tests/resilience/test_resilience_truth.py`` scans the source to
  keep it that way.
* ``__init__`` hardcoded a ``code_sha`` literal and hashed it into the
  ``evaluation_id``, so provenance and the identity of every evaluation were
  pinned to a commit that had nothing to do with the running build. The real
  release SHA is used instead.
"""

from __future__ import annotations

import hashlib
import math
from typing import Sequence

from services.zonepilot.release import current_release_sha
from services.zonepilot.resilience.contracts import (
    BASIS_POINTS,
    FrozenScenarioInputs,
    MetricUnavailable,
    ResilienceEvaluationResult,
    ResilienceMetrics,
    ResilienceScenario,
    ScenarioComparison,
)
from services.zonepilot.resilience.derivation import DerivedCounts, derive_counts

NO_DURATIONS_REASON = (
    "no zone had a routable duration under this scenario, so no travel-time distribution exists to quantise"
)


def compute_metrics(
    durations: Sequence[int],
    *,
    total_demands: int | None,
    covered_demands: int | None,
    total_capacity: int | None,
    lost_capacity: int | None,
    zone_count: int | None,
    disconnected_count: int | None,
    redundant_facility_count: int | None,
    total_open_facilities: int | None,
    coverage_unavailable_reason: str | None = None,
    redundancy_unavailable_reason: str | None = None,
    capacity_unavailable_reason: str | None = None,
) -> ResilienceMetrics:
    """Assemble metrics from derived counts.

    Every argument may be ``None``, meaning "this input was not derivable". A
    ``None`` input produces an UNAVAILABLE metric with a reason attached; it
    never produces a zero. Callers pass reasons through so the record explains
    the gap in the terms the derivation used.
    """
    unavailable: list[MetricUnavailable] = []

    def unavailable_metric(metric: str, reason: str) -> None:
        unavailable.append(MetricUnavailable(metric=metric, reason=reason))

    # --- travel-time quantiles -------------------------------------------------
    p50: int | None = None
    p90: int | None = None
    p95: int | None = None
    if durations:
        sorted_d = sorted(int(value) for value in durations)
        n = len(sorted_d)

        def quantile(q: float) -> int:
            idx = int(math.ceil(q * n)) - 1
            return sorted_d[max(0, min(idx, n - 1))]

        p50 = quantile(0.50)
        p90 = max(p50, quantile(0.90))
        p95 = max(p90, quantile(0.95))
    else:
        for metric in ("p50_duration_seconds", "p90_duration_seconds", "p95_duration_seconds"):
            unavailable_metric(metric, NO_DURATIONS_REASON)

    # --- coverage --------------------------------------------------------------
    coverage_bps: int | None = None
    if covered_demands is None or total_demands is None:
        unavailable_metric(
            "coverage_basis_points",
            coverage_unavailable_reason or "covered and total demand counts were not derivable from the frozen inputs",
        )
    elif total_demands <= 0:
        unavailable_metric(
            "coverage_basis_points",
            "the frozen matrix carries no demand zones, so a coverage fraction has no denominator",
        )
    else:
        coverage_bps = max(0, min(BASIS_POINTS, int((covered_demands / total_demands) * BASIS_POINTS)))

    # --- capacity loss ---------------------------------------------------------
    cap_loss_bps: int | None = None
    if lost_capacity == 0:
        # Nothing was removed, so the fraction lost is zero regardless of the
        # unknown total. This is the only zero produced without a capacity ledger.
        cap_loss_bps = 0
    elif lost_capacity is None or total_capacity is None:
        unavailable_metric(
            "capacity_loss_basis_points",
            capacity_unavailable_reason or "no frozen facility-capacity assumption exists for this evaluation",
        )
    elif total_capacity <= 0:
        unavailable_metric(
            "capacity_loss_basis_points",
            "the frozen capacity assumption totals zero units, so a lost fraction has no denominator",
        )
    else:
        cap_loss_bps = max(0, min(BASIS_POINTS, int((lost_capacity / total_capacity) * BASIS_POINTS)))

    # --- disconnected zones ----------------------------------------------------
    if disconnected_count is None:
        unavailable_metric(
            "disconnected_zones_count",
            "reachability was not derivable from the frozen inputs",
        )

    # --- redundancy ------------------------------------------------------------
    redundancy_bps: int | None = None
    if redundant_facility_count is None or total_open_facilities is None:
        unavailable_metric(
            "redundancy_index_basis_points",
            redundancy_unavailable_reason or "the redundant-facility count was not derivable from the frozen inputs",
        )
    elif total_open_facilities <= 0:
        unavailable_metric(
            "redundancy_index_basis_points",
            "the scenario leaves no facility open, so a redundancy share has no denominator",
        )
    else:
        redundancy_bps = max(
            0, min(BASIS_POINTS, int((redundant_facility_count / total_open_facilities) * BASIS_POINTS))
        )

    # --- failure exposure ------------------------------------------------------
    # Exposure combines the disconnected share with the capacity-loss share. If
    # either component is unavailable the composite is unavailable too; it is not
    # silently recomputed over whichever half survived.
    exposure: int | None = None
    if disconnected_count is None or zone_count is None or zone_count <= 0:
        unavailable_metric(
            "failure_exposure_score",
            "exposure needs a disconnected-zone share, which was not derivable from the frozen inputs",
        )
    elif cap_loss_bps is None:
        unavailable_metric(
            "failure_exposure_score",
            "exposure weights capacity loss, which is unavailable for this evaluation",
        )
    else:
        exposure = int(((disconnected_count / zone_count) * 0.5 + (cap_loss_bps / BASIS_POINTS) * 0.5) * BASIS_POINTS)
        exposure = max(0, min(BASIS_POINTS, exposure))

    return ResilienceMetrics(
        coverage_basis_points=coverage_bps,
        p50_duration_seconds=p50,
        p90_duration_seconds=p90,
        p95_duration_seconds=p95,
        disconnected_zones_count=disconnected_count,
        redundancy_index_basis_points=redundancy_bps,
        failure_exposure_score=exposure,
        capacity_loss_basis_points=cap_loss_bps,
        unavailable=tuple(unavailable),
    )


def metrics_from_counts(counts: DerivedCounts) -> ResilienceMetrics:
    """Build metrics straight from the derivation, carrying its reasons through."""
    return compute_metrics(
        counts.assigned_durations_seconds,
        total_demands=counts.total_demands,
        covered_demands=counts.covered_demands,
        total_capacity=counts.total_capacity,
        lost_capacity=counts.lost_capacity,
        zone_count=counts.zone_count,
        disconnected_count=counts.disconnected_count,
        redundant_facility_count=counts.redundant_facility_count,
        total_open_facilities=counts.total_open_facilities,
        coverage_unavailable_reason=counts.coverage_unavailable_reason,
        redundancy_unavailable_reason=counts.redundancy_unavailable_reason,
        capacity_unavailable_reason=counts.capacity_unavailable_reason,
    )


UNAVAILABLE_GRADE = "UNAVAILABLE"


def compare_scenarios(
    baseline: ResilienceMetrics,
    stressed: ResilienceMetrics,
    baseline_id: str,
    stressed_id: str,
) -> ScenarioComparison:
    """Compare two evaluations, refusing to grade on metrics nobody computed."""
    cov_delta: int | None = None
    if baseline.coverage_basis_points is not None and stressed.coverage_basis_points is not None:
        cov_delta = stressed.coverage_basis_points - baseline.coverage_basis_points

    p95_delta_s: int | None = None
    p95_inflation_bps: int | None = None
    if baseline.p95_duration_seconds is not None and stressed.p95_duration_seconds is not None:
        p95_delta_s = stressed.p95_duration_seconds - baseline.p95_duration_seconds
        if baseline.p95_duration_seconds > 0:
            p95_inflation_bps = int((p95_delta_s / baseline.p95_duration_seconds) * BASIS_POINTS)

    disc_delta: int | None = None
    if baseline.disconnected_zones_count is not None and stressed.disconnected_zones_count is not None:
        disc_delta = max(0, stressed.disconnected_zones_count - baseline.disconnected_zones_count)

    if cov_delta is None or p95_inflation_bps is None:
        grade = UNAVAILABLE_GRADE
    elif p95_inflation_bps <= 1_000 and cov_delta >= 0:
        grade = "ROBUST"
    elif p95_inflation_bps <= 2_500 and cov_delta >= -500:
        grade = "MODERATE_DEGRADATION"
    elif p95_inflation_bps <= 5_000 and cov_delta >= -1_500:
        grade = "SEVERE_DEGRADATION"
    else:
        grade = "CRITICAL_FAILURE"

    return ScenarioComparison(
        baseline_scenario_id=baseline_id,
        stressed_scenario_id=stressed_id,
        coverage_delta_basis_points=cov_delta,
        p95_inflation_seconds=p95_delta_s,
        p95_inflation_basis_points=p95_inflation_bps,
        additional_disconnected_zones=disc_delta,
        capacity_loss_basis_points=stressed.capacity_loss_basis_points,
        resilience_grade=grade,
    )


class ResilienceEngine:
    """Evaluates a scenario against frozen, authentic inputs.

    ``code_sha`` defaults to the running release SHA rather than a literal, and
    it participates in the ``evaluation_id`` hash so two evaluations of the same
    scenario under different builds are distinguishable.
    """

    def __init__(self, code_sha: str | None = None) -> None:
        sha = (code_sha or current_release_sha()).strip()
        if not sha:
            raise ValueError("code_sha must not be empty; evaluation provenance cannot be invented")
        self.code_sha = sha

    def evaluate_scenario(
        self,
        scenario: ResilienceScenario,
        inputs: FrozenScenarioInputs,
        *,
        baseline_metrics: ResilienceMetrics | None = None,
        baseline_id: str = "s1_free_flow",
    ) -> ResilienceEvaluationResult:
        if not isinstance(inputs, FrozenScenarioInputs):
            raise TypeError(
                "evaluate_scenario requires FrozenScenarioInputs built from the authentic travel matrix; "
                "a bare duration sequence carries no provenance and cannot support derived metrics"
            )

        metrics = metrics_from_counts(derive_counts(inputs))

        comparison = None
        if baseline_metrics is not None:
            comparison = compare_scenarios(baseline_metrics, metrics, baseline_id, scenario.scenario_id)

        eval_id = hashlib.sha256(
            f"{scenario.scenario_id}:{scenario.seed}:{inputs.inputs_sha256}:{self.code_sha}".encode("utf-8")
        ).hexdigest()[:16]

        return ResilienceEvaluationResult(
            evaluation_id=f"eval-{eval_id}",
            scenario=scenario,
            metrics=metrics,
            inputs=inputs,
            baseline_comparison=comparison,
            code_sha=self.code_sha,
            fail_closed=not metrics.is_complete,
        )
