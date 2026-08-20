"""PostgreSQL Repository for durable Resilience Scenarios and Evaluation Results.

Ordering matters here (F-010, reopened). The service used to write the scenario
row first and resolve the authentic travel matrix afterwards, so a missing
matrix left an orphan scenario with no evaluation behind it -- a request that
produced no result still looked like a run that happened. Persistence is now a
single transaction: either a scenario and its evaluation both land, or nothing
does.

The result table's metric columns are ``NOT NULL``, so an UNAVAILABLE metric has
no representation in it. Rather than substitute a zero, :meth:`save_evaluation`
refuses to write an incomplete evaluation at all.
"""

from __future__ import annotations

import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from services.common.db_dsn import get_database_dsn
from services.zonepilot.resilience.contracts import METRIC_FIELDS, ResilienceMetrics


class IncompleteEvaluationError(ValueError):
    """An evaluation carrying UNAVAILABLE metrics cannot be persisted."""


class ResilienceRepository:
    def __init__(self, dsn: str | None = None) -> None:
        self._explicit_dsn = dsn

    @property
    def dsn(self) -> str:
        """Resolve the DSN lazily, at connection time rather than construction.

        Repositories used to call get_database_dsn() in __init__. Routers build
        them at module scope, so importing the API package required database
        configuration to already be present: an unset DATABASE_URL made the
        process unimportable, took liveness down with it, and turned 18 test
        modules into collection errors instead of clean skips (F-024).
        """
        return self._explicit_dsn or get_database_dsn()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=15)

    @staticmethod
    def _scenario_insert() -> str:
        return """
            INSERT INTO public.resilience_scenarios (
                scenario_id, workspace_id, scenario_type, description,
                evidence_class, parameters, seed, graph_version, created_by
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s::jsonb, %s, %s, %s::uuid
            )
            ON CONFLICT (scenario_id) DO UPDATE SET
                description = EXCLUDED.description,
                parameters = EXCLUDED.parameters
            RETURNING *
        """

    @staticmethod
    def _result_insert() -> str:
        return """
            INSERT INTO public.resilience_results (
                evaluation_id, scenario_id, workspace_id, coverage_basis_points,
                p50_duration_seconds, p90_duration_seconds, p95_duration_seconds,
                disconnected_zones_count, redundancy_index_basis_points, failure_exposure_score,
                capacity_loss_basis_points, degradation_grade, baseline_comparison, code_sha,
                metric_unavailable
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s::jsonb, %s,
                %s::jsonb
            )
            ON CONFLICT (evaluation_id) DO UPDATE SET
                degradation_grade = EXCLUDED.degradation_grade,
                code_sha = EXCLUDED.code_sha,
                metric_unavailable = EXCLUDED.metric_unavailable
            RETURNING *
        """

    @staticmethod
    def _scenario_params(
        *,
        scenario_id: str,
        workspace_id: str,
        scenario_type: str,
        description: str,
        evidence_class: str,
        parameters: dict[str, Any] | None,
        seed: int,
        graph_version: str,
        created_by: str | None,
    ) -> tuple[Any, ...]:
        created_by_val = created_by if (created_by and len(created_by) == 36 and "-" in created_by) else None
        return (
            scenario_id,
            workspace_id,
            scenario_type,
            description,
            evidence_class,
            json.dumps(parameters or {}),
            seed,
            graph_version,
            created_by_val,
        )

    @staticmethod
    def _unavailability_map(metrics: ResilienceMetrics) -> str:
        """Serialise why each uncomputed metric is uncomputed.

        Migration 20260820002000 made the metric columns nullable and added
        metric_unavailable. Before it, every column was NOT NULL, so an evaluation
        that legitimately could not compute a metric had nowhere to say so -- the
        old code filled the gap with invented constants, and removing the invention
        left this repository refusing to persist anything at all, discarding the
        metrics it HAD derived.

        NULL now means "not computed" and this map records why, per metric. The two
        are written together: a NULL with no reason would be indistinguishable from
        a bug, so the pairing is enforced here rather than left to convention.
        """
        return json.dumps({entry.metric: entry.reason for entry in metrics.unavailable})

    @staticmethod
    def _require_explained(metrics: ResilienceMetrics) -> None:
        """A gap may be persisted; an UNEXPLAINED gap may not."""
        explained = {entry.metric for entry in metrics.unavailable}
        unexplained = [field for field in METRIC_FIELDS if getattr(metrics, field) is None and field not in explained]
        if unexplained:
            raise IncompleteEvaluationError(
                "METRICS_UNAVAILABLE: refusing to persist an evaluation whose missing metrics carry no "
                f"reason: {', '.join(sorted(unexplained))}. An unexplained NULL is a defect, not an absence."
            )

    @staticmethod
    def _require_code_sha(code_sha: str) -> str:
        if not code_sha or not code_sha.strip():
            raise ValueError("code_sha is required; evaluation provenance cannot be invented")
        return code_sha.strip()

    def save_evaluation(
        self,
        *,
        scenario_id: str,
        workspace_id: str,
        scenario_type: str,
        description: str,
        parameters: dict[str, Any] | None,
        seed: int,
        graph_version: str,
        created_by: str | None,
        evaluation_id: str,
        metrics: ResilienceMetrics,
        degradation_grade: str,
        code_sha: str,
        evidence_class: str = "SIMULATED",
        baseline_comparison: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist the scenario and its evaluation atomically, or persist nothing.

        Both inserts share one transaction, so a failure on the result leaves no
        scenario row behind. Validation happens before the connection is opened
        so an unpersistable evaluation never reaches the database at all.
        """
        self._require_explained(metrics)
        sha = self._require_code_sha(code_sha)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._scenario_insert(),
                    self._scenario_params(
                        scenario_id=scenario_id,
                        workspace_id=workspace_id,
                        scenario_type=scenario_type,
                        description=description,
                        evidence_class=evidence_class,
                        parameters=parameters,
                        seed=seed,
                        graph_version=graph_version,
                        created_by=created_by,
                    ),
                )
                scenario_row = cur.fetchone()
                cur.execute(
                    self._result_insert(),
                    (
                        evaluation_id,
                        scenario_id,
                        workspace_id,
                        *(getattr(metrics, field) for field in METRIC_FIELDS),
                        degradation_grade,
                        json.dumps(baseline_comparison) if baseline_comparison else None,
                        sha,
                        self._unavailability_map(metrics),
                    ),
                )
                result_row = cur.fetchone()
            conn.commit()

        merged: dict[str, Any] = dict(scenario_row or {})
        merged.update(dict(result_row or {}))
        return merged

    def get_scenario(self, scenario_id: str, workspace_id: str) -> dict[str, Any] | None:
        """Fetch a scenario, strictly scoped to the owning workspace."""
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("get_scenario requires a non-empty workspace_id")

        with self._connect() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT s.*, r.evaluation_id, r.coverage_basis_points, r.p50_duration_seconds,
                           r.p90_duration_seconds, r.p95_duration_seconds, r.disconnected_zones_count,
                           r.redundancy_index_basis_points, r.failure_exposure_score, r.capacity_loss_basis_points,
                           r.degradation_grade, r.baseline_comparison, r.evaluated_at
                    FROM public.resilience_scenarios s
                    LEFT JOIN public.resilience_results r ON r.scenario_id = s.scenario_id
                    WHERE s.scenario_id = %s
                """
                query += " AND s.workspace_id = %s"
                params: list[Any] = [scenario_id, workspace_id]
                cur.execute(query, params)
                return cur.fetchone()

    def list_scenarios(self, workspace_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.*, r.coverage_basis_points, r.p95_duration_seconds, r.degradation_grade
                    FROM public.resilience_scenarios s
                    LEFT JOIN public.resilience_results r ON r.scenario_id = s.scenario_id
                    WHERE s.workspace_id = %s
                    ORDER BY s.created_at DESC
                    LIMIT %s
                    """,
                    (workspace_id, limit),
                )
                return cur.fetchall()

    def save_result(
        self,
        *,
        evaluation_id: str,
        scenario_id: str,
        workspace_id: str,
        metrics: ResilienceMetrics,
        degradation_grade: str,
        code_sha: str,
        baseline_comparison: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Write an evaluation for an already-persisted scenario.

        Kept for callers that re-evaluate an existing scenario. It takes the
        metrics object rather than loose integers so an unavailable metric
        cannot be flattened into a zero on the way in, and ``code_sha`` has no
        default -- it previously carried a literal SHA, which is invented
        provenance (F-011).
        """
        self._require_explained(metrics)
        sha = self._require_code_sha(code_sha)

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._result_insert(),
                    (
                        evaluation_id,
                        scenario_id,
                        workspace_id,
                        *(getattr(metrics, field) for field in METRIC_FIELDS),
                        degradation_grade,
                        json.dumps(baseline_comparison) if baseline_comparison else None,
                        sha,
                        self._unavailability_map(metrics),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
            return row
