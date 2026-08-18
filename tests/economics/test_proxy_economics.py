"""Tests for R5 Proxy Economics and Canonical Experiment Registry."""

from __future__ import annotations

import pytest

from services.temporal.contracts import EvidenceClass
from services.zonepilot.economics.contracts import (
    ExperimentStatus,
)
from services.zonepilot.economics.registry import (
    CANONICAL_EXPERIMENTS,
    compute_proxy_economics,
    evaluate_experiment,
)


def test_canonical_experiments_registry() -> None:
    exp_ids = [e.experiment_id for e in CANONICAL_EXPERIMENTS]
    assert "EXP-01" in exp_ids
    assert "EXP-02" in exp_ids
    assert "EXP-03" in exp_ids
    assert "EXP-04" in exp_ids

    for exp in CANONICAL_EXPERIMENTS:
        assert exp.status == ExperimentStatus.FROZEN
        assert exp.evidence_class == EvidenceClass.DERIVED
        assert len(exp.hypothesis) > 10


def test_proxy_economics_computation() -> None:
    durations = [600, 750, 900, 1050, 1200]
    demands = [10, 15, 20, 15, 10]
    fixed_cost = 4000

    metrics = compute_proxy_economics(
        fixed_costs=fixed_cost,
        durations=durations,
        demands=demands,
        baseline_p95_seconds=1500,
        baseline_coverage_bps=9500,
    )

    assert metrics.total_fixed_cost_units == 4000
    assert metrics.total_variable_cost_proxy > 0
    assert metrics.cost_per_coverage_point > 0
    assert metrics.cost_per_p95_minute_reduced > 0
    assert metrics.incremental_resilience_proxy_cost == 480.0
    assert metrics.evidence_class == EvidenceClass.ASSUMPTION


def test_experiment_evaluation() -> None:
    res = evaluate_experiment("EXP-01", baseline_val=100.0, treatment_val=85.0)
    assert res.experiment_id == "EXP-01"
    assert res.hypothesis_confirmed is True
    assert res.effect_size == -15.0
    assert res.definition.title == "Early Network Degradation"

    with pytest.raises(ValueError, match="not registered"):
        evaluate_experiment("EXP-UNKNOWN", baseline_val=1.0, treatment_val=2.0)
