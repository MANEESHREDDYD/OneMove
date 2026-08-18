"""PostgreSQL Repository for durable Resilience Scenarios and Evaluation Results."""

from __future__ import annotations

import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from services.common.db_dsn import get_database_dsn


class ResilienceRepository:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or get_database_dsn()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=15)

    def save_scenario(
        self,
        *,
        scenario_id: str,
        workspace_id: str,
        scenario_type: str,
        description: str,
        evidence_class: str = "SIMULATED",
        parameters: dict[str, Any] | None = None,
        seed: int = 42,
        graph_version: str = "1.1",
        created_by: str | None = None,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                created_by_val = created_by if (created_by and len(created_by) == 36 and "-" in created_by) else None
                cur.execute(
                    """
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
                    """,
                    (
                        scenario_id,
                        workspace_id,
                        scenario_type,
                        description,
                        evidence_class,
                        json.dumps(parameters or {}),
                        seed,
                        graph_version,
                        created_by_val,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
            return row

    def get_scenario(self, scenario_id: str, workspace_id: str | None = None) -> dict[str, Any] | None:
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
                params: list[Any] = [scenario_id]
                if workspace_id:
                    query += " AND s.workspace_id = %s"
                    params.append(workspace_id)
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
        coverage_basis_points: int,
        p50_duration_seconds: int,
        p90_duration_seconds: int,
        p95_duration_seconds: int,
        disconnected_zones_count: int,
        redundancy_index_basis_points: int,
        failure_exposure_score: int,
        capacity_loss_basis_points: int,
        degradation_grade: str,
        baseline_comparison: dict[str, Any] | None = None,
        code_sha: str = "c7e24e8d378db6a2f19048993bb3803e76f125c2",
    ) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.resilience_results (
                        evaluation_id, scenario_id, workspace_id, coverage_basis_points,
                        p50_duration_seconds, p90_duration_seconds, p95_duration_seconds,
                        disconnected_zones_count, redundancy_index_basis_points, failure_exposure_score,
                        capacity_loss_basis_points, degradation_grade, baseline_comparison, code_sha
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s::jsonb, %s
                    )
                    ON CONFLICT (evaluation_id) DO UPDATE SET
                        degradation_grade = EXCLUDED.degradation_grade
                    RETURNING *
                    """,
                    (
                        evaluation_id,
                        scenario_id,
                        workspace_id,
                        coverage_basis_points,
                        p50_duration_seconds,
                        p90_duration_seconds,
                        p95_duration_seconds,
                        disconnected_zones_count,
                        redundancy_index_basis_points,
                        failure_exposure_score,
                        capacity_loss_basis_points,
                        degradation_grade,
                        json.dumps(baseline_comparison) if baseline_comparison else None,
                        code_sha,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
            return row
