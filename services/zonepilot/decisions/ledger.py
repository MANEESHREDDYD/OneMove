"""R7 Decision Ledger, Time Travel, Replay, and Shadow Evaluation implementation."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any, Sequence

from services.temporal.contracts import OutcomeStatus
from services.zonepilot.decisions.contracts import (
    DecisionRecord,
    DecisionReplayResult,
    ShadowEvaluation,
    ShadowState,
)


class DecisionLedger:
    def __init__(self, code_sha: str = "8ba985657af312a6ac770f66663c7c3270418932") -> None:
        self.code_sha = code_sha
        self._records: dict[str, DecisionRecord] = {}
        self._shadows: dict[str, ShadowEvaluation] = {}

    def record_decision(
        self,
        *,
        workspace_id: str,
        decision_time: datetime,
        network_version: str,
        dataset_version: str,
        feature_snapshot_hash: str,
        selected_action: str,
        opened_facilities: Sequence[str],
        objective_value: int,
        expected_travel_seconds: int,
        p95_travel_seconds: int,
        coverage_basis_points: int,
        graph_version: str,
        osrm_bundle_hash: str,
        solver_version: str,
        evidence_ids: Sequence[str] = (),
        recorded_at: datetime | None = None,
    ) -> DecisionRecord:
        h = hashlib.sha256(
            f"{workspace_id}:{decision_time.isoformat()}:{selected_action}:{','.join(sorted(opened_facilities))}:{self.code_sha}".encode()
        ).hexdigest()[:16]
        dec_id = f"dec-{h}"
        rec_time = recorded_at or datetime.now(timezone.utc)
        if decision_time > rec_time:
            rec_time = decision_time

        rec = DecisionRecord(
            decision_id=dec_id,
            workspace_id=workspace_id,
            decision_time=decision_time,
            network_version=network_version,
            dataset_version=dataset_version,
            feature_snapshot_hash=feature_snapshot_hash,
            selected_action=selected_action,
            opened_facilities=tuple(sorted(opened_facilities)),
            objective_value=objective_value,
            expected_travel_seconds=expected_travel_seconds,
            p95_travel_seconds=p95_travel_seconds,
            coverage_basis_points=coverage_basis_points,
            graph_version=graph_version,
            osrm_bundle_hash=osrm_bundle_hash,
            solver_version=solver_version,
            code_sha=self.code_sha,
            evidence_ids=tuple(evidence_ids),
            recorded_at=rec_time,
        )
        self._records[dec_id] = rec
        return rec

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        return self._records.get(decision_id)

    def list_decisions(self, workspace_id: str | None = None) -> list[DecisionRecord]:
        if workspace_id is None:
            return list(self._records.values())
        return [r for r in self._records.values() if r.workspace_id == workspace_id]

    def replay_decision(
        self,
        original_decision_id: str,
        *,
        recomputed_action: str,
        recomputed_facilities: Sequence[str],
        recomputed_objective: int,
    ) -> DecisionReplayResult:
        orig = self.get_decision(original_decision_id)
        if orig is None:
            raise ValueError(f"Decision {original_decision_id} not found in ledger")

        action_match = (orig.selected_action == recomputed_action)
        facilities_match = (set(orig.opened_facilities) == set(recomputed_facilities))
        obj_match = (orig.objective_value == recomputed_objective)

        return DecisionReplayResult(
            original_decision_id=original_decision_id,
            pit_valid=True,
            reproduced_exact_action=action_match,
            reproduced_exact_facilities=facilities_match,
            objective_match=obj_match,
            code_sha=self.code_sha,
        )

    def create_shadow(
        self,
        decision: DecisionRecord,
        future_observation_time: datetime,
    ) -> ShadowEvaluation:
        shadow_id = f"shad-{decision.decision_id[4:]}"
        shad = ShadowEvaluation(
            shadow_id=shadow_id,
            decision_id=decision.decision_id,
            frozen_decision_time=decision.decision_time,
            future_observation_time=future_observation_time,
            shadow_state=ShadowState.FROZEN_AWAITING_FUTURE,
            predicted_p95_seconds=decision.p95_travel_seconds,
            outcome_status=OutcomeStatus.PENDING,
        )
        self._shadows[shadow_id] = shad
        return shad

    def evaluate_shadow(
        self,
        shadow_id: str,
        actual_observed_p95_seconds: int,
    ) -> ShadowEvaluation:
        shad = self._shadows.get(shadow_id)
        if shad is None:
            raise ValueError(f"Shadow {shadow_id} not found")

        regret = max(0, actual_observed_p95_seconds - shad.predicted_p95_seconds)
        evaluated = ShadowEvaluation(
            shadow_id=shadow_id,
            decision_id=shad.decision_id,
            frozen_decision_time=shad.frozen_decision_time,
            future_observation_time=shad.future_observation_time,
            shadow_state=ShadowState.EVALUATED,
            predicted_p95_seconds=shad.predicted_p95_seconds,
            actual_observed_p95_seconds=actual_observed_p95_seconds,
            regret_seconds=regret,
            outcome_status=OutcomeStatus.EVALUATED,
            evaluated_at=datetime.now(timezone.utc),
        )
        self._shadows[shadow_id] = evaluated
        return evaluated
