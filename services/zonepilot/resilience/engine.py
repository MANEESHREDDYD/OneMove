"""Core R4 Network Resilience evaluation engine."""

from __future__ import annotations

import hashlib
import math
from typing import Sequence

from services.zonepilot.resilience.contracts import (
    ResilienceEvaluationResult,
    ResilienceMetrics,
    ResilienceScenario,
    ScenarioComparison,
)


def compute_metrics(
    durations: Sequence[int],
    *,
    total_demands: int,
    covered_demands: int,
    total_capacity: int,
    lost_capacity: int,
    zone_count: int,
    disconnected_count: int,
    redundant_facility_count: int,
    total_open_facilities: int,
) -> ResilienceMetrics:
    if not durations:
        return ResilienceMetrics(
            coverage_basis_points=0,
            p50_duration_seconds=0,
            p90_duration_seconds=0,
            p95_duration_seconds=0,
            disconnected_zones_count=zone_count,
            redundancy_index_basis_points=0,
            failure_exposure_score=10_000,
            capacity_loss_basis_points=10_000 if total_capacity > 0 else 0,
        )

    sorted_d = sorted(durations)
    n = len(sorted_d)

    def quantile(q: float) -> int:
        idx = int(math.ceil(q * n)) - 1
        return sorted_d[max(0, min(idx, n - 1))]

    p50 = quantile(0.50)
    p90 = quantile(0.90)
    p95 = quantile(0.95)

    coverage_bps = int((covered_demands / total_demands) * 10_000) if total_demands > 0 else 0
    cap_loss_bps = int((lost_capacity / total_capacity) * 10_000) if total_capacity > 0 else 0
    redundancy_bps = int((redundant_facility_count / max(1, total_open_facilities)) * 10_000)

    # Exposure score combines disconnected zones and high latency ratio
    exposure = int(((disconnected_count / max(1, zone_count)) * 0.5 + (cap_loss_bps / 10_000) * 0.5) * 10_000)

    return ResilienceMetrics(
        coverage_basis_points=max(0, min(10_000, coverage_bps)),
        p50_duration_seconds=p50,
        p90_duration_seconds=max(p50, p90),
        p95_duration_seconds=max(p90, p95),
        disconnected_zones_count=disconnected_count,
        redundancy_index_basis_points=max(0, min(10_000, redundancy_bps)),
        failure_exposure_score=max(0, min(10_000, exposure)),
        capacity_loss_basis_points=max(0, min(10_000, cap_loss_bps)),
    )


def compare_scenarios(
    baseline: ResilienceMetrics,
    stressed: ResilienceMetrics,
    baseline_id: str,
    stressed_id: str,
) -> ScenarioComparison:
    cov_delta = stressed.coverage_basis_points - baseline.coverage_basis_points
    p95_delta_s = stressed.p95_duration_seconds - baseline.p95_duration_seconds
    p95_inflation_bps = (
        int((p95_delta_s / max(1, baseline.p95_duration_seconds)) * 10_000) if baseline.p95_duration_seconds > 0 else 0
    )
    disc_delta = max(0, stressed.disconnected_zones_count - baseline.disconnected_zones_count)

    # Compute resilience grade
    if p95_inflation_bps <= 1_000 and cov_delta >= 0:
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
    def __init__(self, code_sha: str = "8ba985657af312a6ac770f66663c7c3270418932") -> None:
        self.code_sha = code_sha

    def evaluate_scenario(
        self,
        scenario: ResilienceScenario,
        durations: Sequence[int],
        *,
        total_demands: int = 94,
        covered_demands: int = 94,
        total_capacity: int = 1200,
        lost_capacity: int = 0,
        zone_count: int = 94,
        disconnected_count: int = 0,
        redundant_facility_count: int = 2,
        total_open_facilities: int = 4,
        baseline_metrics: ResilienceMetrics | None = None,
        baseline_id: str = "s1_free_flow",
    ) -> ResilienceEvaluationResult:
        metrics = compute_metrics(
            durations,
            total_demands=total_demands,
            covered_demands=covered_demands,
            total_capacity=total_capacity,
            lost_capacity=lost_capacity,
            zone_count=zone_count,
            disconnected_count=disconnected_count,
            redundant_facility_count=redundant_facility_count,
            total_open_facilities=total_open_facilities,
        )

        comparison = None
        if baseline_metrics is not None:
            comparison = compare_scenarios(baseline_metrics, metrics, baseline_id, scenario.scenario_id)

        eval_id = hashlib.sha256(
            f"{scenario.scenario_id}:{scenario.seed}:{metrics.p95_duration_seconds}:{self.code_sha}".encode("utf-8")
        ).hexdigest()[:16]

        return ResilienceEvaluationResult(
            evaluation_id=f"eval-{eval_id}",
            scenario=scenario,
            metrics=metrics,
            baseline_comparison=comparison,
            code_sha=self.code_sha,
            fail_closed=False,
        )
