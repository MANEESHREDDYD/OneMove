"""PostgreSQL Repository for durable Decision Records, Replays, and Shadows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

import psycopg
from psycopg.rows import dict_row

from services.common.db_dsn import get_database_dsn
from services.zonepilot.decisions.contracts import (
    DecisionRecord,
    ShadowEvaluation,
)


class DecisionRepository:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or get_database_dsn()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=15)

    def verify_snapshot_pit(self, snapshot_hash: str, decision_time: datetime) -> bool:
        """Query temporal records/manifests to prove information_available_at <= decision_time."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                # Check temporal feature_records if present
                cur.execute(
                    """
                    SELECT COUNT(*) as cnt FROM zonepilot_temporal.feature_records
                    WHERE information_available_at > %s
                      AND feature_values->>'snapshot_hash' = %s
                    """,
                    (decision_time, snapshot_hash),
                )
                row = cur.fetchone()
                if row and row.get("cnt", 0) > 0:
                    return False
        return True

    def record_decision(
        self,
        decision: DecisionRecord,
        recorded_by: str | None = None,
    ) -> DecisionRecord:
        with self._connect() as conn:
            with conn.cursor() as cur:
                rec_by_val = recorded_by if (recorded_by and len(recorded_by) == 36 and "-" in recorded_by) else None
                cur.execute(
                    """
                    INSERT INTO public.decision_records (
                        decision_id, workspace_id, decision_time, network_version,
                        dataset_version, feature_snapshot_hash, selected_action,
                        opened_facilities, objective_value, expected_travel_seconds,
                        p95_travel_seconds, coverage_basis_points, graph_version,
                        osrm_bundle_hash, solver_version, code_sha, evidence_ids,
                        recorded_at, recorded_by
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s::uuid
                    )
                    ON CONFLICT (decision_id) DO UPDATE SET
                        recorded_at = EXCLUDED.recorded_at
                    RETURNING *
                    """,
                    (
                        decision.decision_id,
                        decision.workspace_id,
                        decision.decision_time,
                        decision.network_version,
                        decision.dataset_version,
                        decision.feature_snapshot_hash,
                        decision.selected_action,
                        list(decision.opened_facilities),
                        decision.objective_value,
                        decision.expected_travel_seconds,
                        decision.p95_travel_seconds,
                        decision.coverage_basis_points,
                        decision.graph_version,
                        decision.osrm_bundle_hash,
                        decision.solver_version,
                        decision.code_sha,
                        list(decision.evidence_ids),
                        decision.recorded_at,
                        rec_by_val,
                    ),
                )
            conn.commit()
            return decision

    def get_decision(self, decision_id: str, workspace_id: str | None = None) -> DecisionRecord | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                query = "SELECT * FROM public.decision_records WHERE decision_id = %s"
                params: list[Any] = [decision_id]
                if workspace_id:
                    query += " AND workspace_id = %s"
                    params.append(workspace_id)
                cur.execute(query, params)
                row = cur.fetchone()
                if not row:
                    return None
                return DecisionRecord(
                    decision_id=row["decision_id"],
                    workspace_id=row["workspace_id"],
                    decision_time=row["decision_time"],
                    network_version=row["network_version"],
                    dataset_version=row["dataset_version"],
                    feature_snapshot_hash=row["feature_snapshot_hash"],
                    selected_action=row["selected_action"],
                    opened_facilities=tuple(row["opened_facilities"]),
                    objective_value=row["objective_value"],
                    expected_travel_seconds=row["expected_travel_seconds"],
                    p95_travel_seconds=row["p95_travel_seconds"],
                    coverage_basis_points=row["coverage_basis_points"],
                    graph_version=row["graph_version"],
                    osrm_bundle_hash=row["osrm_bundle_hash"],
                    solver_version=row["solver_version"],
                    code_sha=row["code_sha"],
                    evidence_ids=tuple(row["evidence_ids"]),
                    recorded_at=row["recorded_at"],
                )

    def list_decisions(self, workspace_id: str, limit: int = 50) -> list[DecisionRecord]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM public.decision_records
                    WHERE workspace_id = %s
                    ORDER BY decision_time DESC
                    LIMIT %s
                    """,
                    (workspace_id, limit),
                )
                rows = cur.fetchall()
                return [
                    DecisionRecord(
                        decision_id=r["decision_id"],
                        workspace_id=r["workspace_id"],
                        decision_time=r["decision_time"],
                        network_version=r["network_version"],
                        dataset_version=r["dataset_version"],
                        feature_snapshot_hash=r["feature_snapshot_hash"],
                        selected_action=r["selected_action"],
                        opened_facilities=tuple(r["opened_facilities"]),
                        objective_value=r["objective_value"],
                        expected_travel_seconds=r["expected_travel_seconds"],
                        p95_travel_seconds=r["p95_travel_seconds"],
                        coverage_basis_points=r["coverage_basis_points"],
                        graph_version=r["graph_version"],
                        osrm_bundle_hash=r["osrm_bundle_hash"],
                        solver_version=r["solver_version"],
                        code_sha=r["code_sha"],
                        evidence_ids=tuple(r["evidence_ids"]),
                        recorded_at=r["recorded_at"],
                    )
                    for r in rows
                ]

    def save_replay(
        self,
        *,
        replay_id: str,
        original_decision_id: str,
        workspace_id: str,
        pit_valid: bool,
        pit_cutoff: datetime,
        reproduced_exact_action: bool,
        reproduced_exact_facilities: bool,
        objective_match: bool,
        recomputed_objective: int,
        recomputed_facilities: Sequence[str],
        code_sha: str,
    ) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.decision_replays (
                        replay_id, original_decision_id, workspace_id, pit_valid,
                        pit_cutoff, reproduced_exact_action, reproduced_exact_facilities,
                        objective_match, recomputed_objective, recomputed_facilities,
                        code_sha
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s
                    )
                    """,
                    (
                        replay_id,
                        original_decision_id,
                        workspace_id,
                        pit_valid,
                        pit_cutoff,
                        reproduced_exact_action,
                        reproduced_exact_facilities,
                        objective_match,
                        recomputed_objective,
                        list(recomputed_facilities),
                        code_sha,
                    ),
                )
            conn.commit()

    def create_shadow(
        self,
        shadow: ShadowEvaluation,
        workspace_id: str,
    ) -> ShadowEvaluation:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.shadow_evaluations (
                        shadow_id, decision_id, workspace_id, frozen_decision_time,
                        future_observation_time, shadow_state, predicted_p95_seconds,
                        outcome_status
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s
                    )
                    ON CONFLICT (shadow_id) DO NOTHING
                    """,
                    (
                        shadow.shadow_id,
                        shadow.decision_id,
                        workspace_id,
                        shadow.frozen_decision_time,
                        shadow.future_observation_time,
                        shadow.shadow_state.value,
                        shadow.predicted_p95_seconds,
                        shadow.outcome_status.value,
                    ),
                )
            conn.commit()
            return shadow
