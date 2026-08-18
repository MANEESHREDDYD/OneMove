"""R7 Decision Ledger, Time Travel, Replay, and Shadow Evaluation implementation."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Sequence

from services.temporal.contracts import OutcomeStatus
from services.zonepilot.decisions.contracts import (
    DecisionRecord,
    DecisionReplayResult,
    ShadowEvaluation,
    ShadowState,
)
from services.zonepilot.decisions.repository import DecisionRepository


class DecisionLedger:
    def __init__(
        self,
        code_sha: str = "c7e24e8d378db6a2f19048993bb3803e76f125c2",
        repository: DecisionRepository | None = None,
    ) -> None:
        self.code_sha = code_sha
        self.repository = repository
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
        recorded_by: str | None = None,
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
        if self.repository:
            try:
                self.repository.record_decision(rec, recorded_by=recorded_by)
            except Exception:
                pass
        return rec

    def get_decision(self, decision_id: str, workspace_id: str | None = None) -> DecisionRecord | None:
        if self.repository:
            try:
                db_rec = self.repository.get_decision(decision_id, workspace_id)
                if db_rec is not None:
                    return db_rec
            except Exception:
                pass
        rec = self._records.get(decision_id)
        if rec and workspace_id and rec.workspace_id != workspace_id:
            return None
        return rec

    def list_decisions(self, workspace_id: str | None = None) -> list[DecisionRecord]:
        if self.repository and workspace_id:
            try:
                db_recs = self.repository.list_decisions(workspace_id)
                if db_recs:
                    return db_recs
            except Exception:
                pass
        if workspace_id is None:
            return list(self._records.values())
        return [r for r in self._records.values() if r.workspace_id == workspace_id]

    def verify_pit_lineage(
        self,
        decision_time: datetime,
        feature_cutoff: datetime | None = None,
    ) -> bool:
        """Verify Point-In-Time causality: features must be available at or before decision_time."""
        cutoff = feature_cutoff or decision_time
        return cutoff <= decision_time

    def replay_decision(
        self,
        original_decision_id: str,
        *,
        recomputed_action: str,
        recomputed_facilities: Sequence[str],
        recomputed_objective: int,
        feature_cutoff: datetime | None = None,
    ) -> DecisionReplayResult:
        orig = self.get_decision(original_decision_id)
        if orig is None:
            raise ValueError(f"Decision {original_decision_id} not found in ledger")

        action_match = orig.selected_action == recomputed_action
        facilities_match = set(orig.opened_facilities) == set(recomputed_facilities)
        obj_match = orig.objective_value == recomputed_objective
        pit_valid = self.verify_pit_lineage(orig.decision_time, feature_cutoff)

        replay_res = DecisionReplayResult(
            original_decision_id=original_decision_id,
            replayed_at=datetime.now(timezone.utc),
            pit_valid=pit_valid,
            reproduced_exact_action=action_match,
            reproduced_exact_facilities=facilities_match,
            objective_match=obj_match,
            code_sha=self.code_sha,
        )

        if self.repository:
            try:
                rep_id = f"rep-{hashlib.sha256(f'{original_decision_id}:{replay_res.replayed_at.isoformat()}'.encode()).hexdigest()[:16]}"
                self.repository.save_replay(
                    replay_id=rep_id,
                    original_decision_id=original_decision_id,
                    workspace_id=orig.workspace_id,
                    pit_valid=pit_valid,
                    pit_cutoff=orig.decision_time,
                    reproduced_exact_action=action_match,
                    reproduced_exact_facilities=facilities_match,
                    objective_match=obj_match,
                    recomputed_objective=recomputed_objective,
                    recomputed_facilities=recomputed_facilities,
                    code_sha=self.code_sha,
                )
            except Exception:
                pass

        return replay_res

    def create_shadow(
        self,
        decision_or_id: DecisionRecord | str,
        future_time: datetime | None = None,
        *,
        frozen_decision_time: datetime | None = None,
        future_observation_time: datetime | None = None,
        predicted_p95_seconds: int | None = None,
    ) -> ShadowEvaluation:
        if isinstance(decision_or_id, DecisionRecord):
            dec_id = decision_or_id.decision_id
            f_time = future_time or future_observation_time
            if f_time is None:
                raise ValueError("future_observation_time required")
            f_decision_time = decision_or_id.decision_time
            p_p95 = decision_or_id.p95_travel_seconds
            ws_id = decision_or_id.workspace_id
        else:
            dec_id = decision_or_id
            f_time = future_observation_time or future_time
            if f_time is None:
                raise ValueError("future_observation_time required")
            f_decision_time = frozen_decision_time or datetime.now(timezone.utc)
            p_p95 = predicted_p95_seconds or 0
            orig = self.get_decision(dec_id)
            ws_id = orig.workspace_id if orig else "ws-default"

        if f_time <= f_decision_time:
            raise ValueError("future_observation_time must be strictly after frozen_decision_time")

        h = hashlib.sha256(
            f"{dec_id}:{f_decision_time.isoformat()}:{f_time.isoformat()}".encode()
        ).hexdigest()[:16]
        shadow_id = f"shd-{h}"

        shadow = ShadowEvaluation(
            shadow_id=shadow_id,
            decision_id=dec_id,
            frozen_decision_time=f_decision_time,
            future_observation_time=f_time,
            shadow_state=ShadowState.FROZEN_AWAITING_FUTURE,
            predicted_p95_seconds=p_p95,
            actual_observed_p95_seconds=None,
            regret_seconds=None,
            outcome_status=OutcomeStatus.PENDING,
            evaluated_at=None,
        )
        self._shadows[shadow_id] = shadow
        if self.repository:
            try:
                self.repository.create_shadow(shadow, workspace_id=ws_id)
            except Exception:
                pass
        return shadow

    def get_shadow(self, shadow_id: str) -> ShadowEvaluation | None:
        return self._shadows.get(shadow_id)

    def evaluate_shadow(
        self,
        shadow_id: str,
        *,
        actual_observed_p95_seconds: int,
        observation_valid_time: datetime | None = None,
    ) -> ShadowEvaluation:
        shadow = self.get_shadow(shadow_id)
        if shadow is None:
            raise ValueError(f"Shadow evaluation {shadow_id} not found")

        obs_time = observation_valid_time or shadow.future_observation_time
        if obs_time < shadow.future_observation_time:
            raise ValueError("Observation is premature for this shadow window")

        regret = actual_observed_p95_seconds - shadow.predicted_p95_seconds
        updated = ShadowEvaluation(
            shadow_id=shadow.shadow_id,
            decision_id=shadow.decision_id,
            frozen_decision_time=shadow.frozen_decision_time,
            future_observation_time=shadow.future_observation_time,
            shadow_state=ShadowState.EVALUATED,
            predicted_p95_seconds=shadow.predicted_p95_seconds,
            actual_observed_p95_seconds=actual_observed_p95_seconds,
            regret_seconds=regret,
            outcome_status=OutcomeStatus.EVALUATED,
            evaluated_at=datetime.now(timezone.utc),
        )
        self._shadows[shadow_id] = updated
        return updated
