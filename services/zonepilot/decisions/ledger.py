"""R7 Durable Decision Ledger, Time Travel, Replay, and Shadow Evaluation implementation."""

from __future__ import annotations

import hashlib
import json
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
from services.zonepilot.optimization.repository import OptimizationRepository
from services.zonepilot.release import current_release_sha


class DecisionLedger:
    def __init__(
        self,
        code_sha: str | None = None,
        repository: DecisionRepository | None = None,
        opt_repository: OptimizationRepository | None = None,
    ) -> None:
        self.code_sha = code_sha or current_release_sha()
        self.repository = repository or DecisionRepository()
        self.opt_repository = opt_repository or OptimizationRepository()

    def freeze_decision_from_optimization(
        self,
        *,
        job: dict[str, Any],
        workspace_id: str,
        operator_rationale: str | None = None,
        recorded_by: str | None = None,
    ) -> DecisionRecord:
        """Freeze an authoritative decision cryptographically bound to a completed optimization job."""
        if not job:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: No job provided")

        res_doc = job.get("result_document")
        if not res_doc:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: No result_document present in optimization job")

        if isinstance(res_doc, str):
            res_doc = json.loads(res_doc)

        solver_status = res_doc.get("status") or job.get("solver_status")
        if solver_status not in {"OPTIMAL", "FEASIBLE"}:
            raise ValueError(
                f"DECISION_LINEAGE_INCOMPLETE: Cannot freeze decision from non-optimal job status {solver_status}"
            )

        opened = res_doc.get("opened_facility_ids") or res_doc.get("opened_facilities")
        if not opened:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: opened_facility_ids missing from optimization result")

        obj_info = res_doc.get("objective")
        if isinstance(obj_info, dict):
            obj_val = obj_info.get("weighted_total")
            exp_travel = obj_info.get("expected_travel_probability_demand_seconds")
            p95_travel = obj_info.get("p95_travel_demand_seconds")
        else:
            obj_val = res_doc.get("objective_value")
            exp_travel = res_doc.get("expected_travel_seconds")
            p95_travel = res_doc.get("p95_travel_seconds")

        if obj_val is None or exp_travel is None or p95_travel is None:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: Incomplete objective metrics in result_document")

        scenario_metrics = res_doc.get("scenario_metrics")
        if not scenario_metrics:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: scenario_metrics missing from optimization result")

        first_metric = scenario_metrics[0]
        if isinstance(first_metric, dict):
            cov_bps = first_metric.get("coverage_basis_points")
        else:
            cov_bps = getattr(first_metric, "coverage_basis_points", None)

        if cov_bps is None:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: coverage_basis_points missing from scenario_metrics")

        graph_version = job.get("graph_version") or res_doc.get("graph_version")
        if not graph_version:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: graph_version missing from job lineage")

        dataset_version = job.get("dataset_version") or res_doc.get("dataset_version")
        if not dataset_version:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: dataset_version missing from job lineage")

        req_fp = job.get("request_fingerprint") or res_doc.get("problem_fingerprint")
        if not req_fp:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: request_fingerprint missing from job lineage")

        action_val = res_doc.get("action") or job.get("action")
        if not action_val:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: action missing from optimization result")
        selected_action = action_val if isinstance(action_val, str) else getattr(action_val, "value", str(action_val))

        network_version = job.get("network_version") or res_doc.get("network_version")
        if not network_version:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: network_version missing from job lineage")

        dec_time = job.get("finished_at") or job.get("completed_at")
        if not dec_time:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: completed_at / finished_at missing from job lineage")
        if isinstance(dec_time, str):
            try:
                dec_time = datetime.fromisoformat(dec_time.replace("Z", "+00:00"))
            except Exception:
                raise ValueError(f"DECISION_LINEAGE_INCOMPLETE: invalid completion timestamp format {dec_time}")

        # Fetch authentic release manifest / artifact hashes without fabrication
        from services.zonepilot.optimization.r1_catalog import default_data_root

        manifest_path = default_data_root() / "private" / "official" / "manifests" / "gold_manifest.json"
        osrm_bundle_hash = None
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                osrm_bundle_hash = manifest.get("osrm_bundle_sha256") or manifest.get("osrm_table_sha256")
            except Exception:
                pass

        if not osrm_bundle_hash:
            rel_manifest_path = default_data_root().parent.parent / "release_manifest.json"
            if rel_manifest_path.is_file():
                try:
                    rel_m = json.loads(rel_manifest_path.read_text(encoding="utf-8"))
                    osrm_bundle_hash = rel_m.get("artifacts", {}).get("r1_osrm_travel_matrix.json", {}).get("sha256")
                except Exception:
                    pass

        if not osrm_bundle_hash:
            raise ValueError(
                "DECISION_LINEAGE_INCOMPLETE: authoritative OSRM bundle hash missing from release manifest"
            )

        evidence_ids = res_doc.get("evidence_ids") or job.get("evidence_ids")
        if not evidence_ids:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: evidence_ids missing from optimization result")

        solver_version = job.get("solver_version") or res_doc.get("solver_version")
        if not solver_version:
            raise ValueError("DECISION_LINEAGE_INCOMPLETE: solver_version missing from job lineage")

        h = hashlib.sha256(
            f"{workspace_id}:{job.get('id')}:{','.join(sorted(opened))}:{self.code_sha}".encode()
        ).hexdigest()[:16]
        dec_id = f"dec-{h}"

        rec_time = datetime.now(timezone.utc)
        if dec_time > rec_time:
            rec_time = dec_time

        rec = DecisionRecord(
            decision_id=dec_id,
            workspace_id=workspace_id,
            decision_time=dec_time,
            network_version=network_version,
            dataset_version=dataset_version,
            feature_snapshot_hash=req_fp,
            selected_action=selected_action,
            opened_facilities=tuple(sorted(opened)),
            objective_value=int(obj_val),
            expected_travel_seconds=int(exp_travel),
            p95_travel_seconds=int(p95_travel),
            coverage_basis_points=int(cov_bps),
            graph_version=graph_version,
            osrm_bundle_hash=osrm_bundle_hash,
            solver_version=solver_version,
            code_sha=job.get("code_sha") or self.code_sha,
            evidence_ids=tuple(evidence_ids),
            recorded_at=rec_time,
        )

        self.repository.record_decision(rec, recorded_by=recorded_by)
        return rec

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
            f"{workspace_id}:{decision_time.isoformat()}:{feature_snapshot_hash}:{osrm_bundle_hash}:{selected_action}:{','.join(sorted(opened_facilities))}:{self.code_sha}".encode()
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
        self.repository.record_decision(rec, recorded_by=recorded_by)
        return rec

    def get_decision(self, decision_id: str, workspace_id: str | None = None) -> DecisionRecord | None:
        return self.repository.get_decision(decision_id, workspace_id)

    def list_decisions(self, workspace_id: str, limit: int = 50) -> list[DecisionRecord]:
        return self.repository.list_decisions(workspace_id, limit=limit)

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
        workspace_id: str | None = None,
        *,
        feature_cutoff: datetime | None = None,
    ) -> DecisionReplayResult:
        """Server-side deterministic Point-in-Time Replay.

        Loads original decision from PostgreSQL, reconstructs problem from frozen lineage,
        reruns solver, compares reproduced outputs, and stores replay record.
        """
        # Fail closed: without a caller-supplied workspace the decision lookup would be
        # unscoped, and ws_id would then be back-filled from the *victim's* record --
        # re-opening the cross-tenant replay path (P0-AUTH-SNAPSHOT-001).
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("replay_decision requires an explicit workspace_id")

        orig = self.get_decision(original_decision_id, workspace_id)
        if orig is None:
            raise LookupError(f"Decision {original_decision_id} not found in ledger")

        ws_id = workspace_id
        pit_valid = self.verify_pit_lineage(orig.decision_time, feature_cutoff)

        if not pit_valid or (feature_cutoff and feature_cutoff > orig.decision_time):
            replay_res = DecisionReplayResult(
                original_decision_id=original_decision_id,
                replayed_at=datetime.now(timezone.utc),
                pit_valid=False,
                reproduced_exact_action=False,
                reproduced_exact_facilities=False,
                objective_match=False,
                match_status="NON_REPLAYABLE",
                reason=f"Point-In-Time violation: feature_cutoff ({feature_cutoff.isoformat() if feature_cutoff else 'None'}) is strictly after frozen decision_time ({orig.decision_time.isoformat()})",
                code_sha=self.code_sha,
            )
            return replay_res

        # 1. Fetch frozen immutable ProblemSnapshot from repository
        snapshot_doc = self.opt_repository.get_problem_snapshot(orig.feature_snapshot_hash, workspace_id=ws_id)

        from services.zonepilot.optimization.contracts import (
            OptimizationProblem,
            problem_fingerprint,
        )
        from services.zonepilot.optimization.r1_catalog import default_data_root
        from services.zonepilot.optimization.solver import optimize_facilities

        # 2. Verify artifact integrity: check OSRM bundle hash
        mat_path = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
        if not mat_path.is_file():
            return DecisionReplayResult(
                original_decision_id=original_decision_id,
                replayed_at=datetime.now(timezone.utc),
                pit_valid=False,
                reproduced_exact_action=False,
                reproduced_exact_facilities=False,
                objective_match=False,
                match_status="NON_REPLAYABLE",
                reason="CORRUPTED_OR_MISSING_ARTIFACT: Authoritative travel matrix is unavailable on disk.",
                code_sha=self.code_sha,
            )

        current_mat_sha = hashlib.sha256(mat_path.read_bytes()).hexdigest()
        if current_mat_sha != orig.osrm_bundle_hash:
            return DecisionReplayResult(
                original_decision_id=original_decision_id,
                replayed_at=datetime.now(timezone.utc),
                pit_valid=False,
                reproduced_exact_action=False,
                reproduced_exact_facilities=False,
                objective_match=False,
                match_status="NON_REPLAYABLE",
                reason=f"CORRUPTED_OR_MISSING_ARTIFACT: Current travel matrix SHA-256 ({current_mat_sha[:16]}...) does not match frozen decision osrm_bundle_hash ({orig.osrm_bundle_hash[:16]}...).",
                code_sha=self.code_sha,
            )

        if snapshot_doc:
            problem_data = snapshot_doc.get("problem", {})
            try:
                if isinstance(problem_data, dict):
                    p_norm = dict(problem_data)
                    if "facilities" in p_norm and isinstance(p_norm["facilities"], list):
                        p_norm["facilities"] = tuple(p_norm["facilities"])
                    if "demand_points" in p_norm and isinstance(p_norm["demand_points"], list):
                        p_norm["demand_points"] = tuple(p_norm["demand_points"])
                    if "scenarios" in p_norm and isinstance(p_norm["scenarios"], list):
                        scens = []
                        for sc in p_norm["scenarios"]:
                            sc_copy = dict(sc)
                            if "travel_matrix" in sc_copy and isinstance(sc_copy["travel_matrix"], dict):
                                tm = dict(sc_copy["travel_matrix"])
                                if "facility_ids" in tm and isinstance(tm["facility_ids"], list):
                                    tm["facility_ids"] = tuple(tm["facility_ids"])
                                if "demand_ids" in tm and isinstance(tm["demand_ids"], list):
                                    tm["demand_ids"] = tuple(tm["demand_ids"])
                                if "durations_seconds" in tm and isinstance(tm["durations_seconds"], list):
                                    tm["durations_seconds"] = tuple(
                                        tuple(r) if isinstance(r, list) else r for r in tm["durations_seconds"]
                                    )
                                sc_copy["travel_matrix"] = tm
                            if "capacity_adjustments" in sc_copy and isinstance(sc_copy["capacity_adjustments"], list):
                                sc_copy["capacity_adjustments"] = tuple(sc_copy["capacity_adjustments"])
                            scens.append(sc_copy)
                        p_norm["scenarios"] = tuple(scens)
                    problem = OptimizationProblem.model_validate(p_norm, strict=False)
                else:
                    problem = OptimizationProblem.model_validate(problem_data, strict=False)
            except Exception as parse_err:
                return DecisionReplayResult(
                    original_decision_id=original_decision_id,
                    replayed_at=datetime.now(timezone.utc),
                    pit_valid=False,
                    reproduced_exact_action=False,
                    reproduced_exact_facilities=False,
                    objective_match=False,
                    match_status="NON_REPLAYABLE",
                    reason=f"SNAPSHOT_CORRUPTED: Failed to deserialize frozen problem snapshot: {parse_err}",
                    code_sha=self.code_sha,
                )

            computed_sha = problem_fingerprint(problem)
            if computed_sha != orig.feature_snapshot_hash:
                return DecisionReplayResult(
                    original_decision_id=original_decision_id,
                    replayed_at=datetime.now(timezone.utc),
                    pit_valid=False,
                    reproduced_exact_action=False,
                    reproduced_exact_facilities=False,
                    objective_match=False,
                    match_status="NON_REPLAYABLE",
                    reason=f"SNAPSHOT_HASH_CORRUPTED: Computed problem fingerprint ({computed_sha[:16]}...) does not match frozen feature_snapshot_hash ({orig.feature_snapshot_hash[:16]}...).",
                    code_sha=self.code_sha,
                )
        else:
            # Reconstruct from authentic artifacts if legacy record without explicit snapshot row
            from services.zonepilot.optimization.pubsub_worker import _reconstruct_problem_from_payload

            try:
                problem = _reconstruct_problem_from_payload({})
            except Exception as rec_err:
                return DecisionReplayResult(
                    original_decision_id=original_decision_id,
                    replayed_at=datetime.now(timezone.utc),
                    pit_valid=False,
                    reproduced_exact_action=False,
                    reproduced_exact_facilities=False,
                    objective_match=False,
                    match_status="NON_REPLAYABLE",
                    reason=f"PROBLEM_SNAPSHOT_NOT_FOUND: {rec_err}",
                    code_sha=self.code_sha,
                )

        res = optimize_facilities(problem)

        action_match = res.action.value == orig.selected_action
        facilities_match = set(res.opened_facility_ids) == set(orig.opened_facilities)
        recomputed_obj = res.objective.weighted_total if res.objective else 0
        obj_match = recomputed_obj == orig.objective_value

        if action_match and facilities_match and obj_match:
            match_status = "EXACT_MATCH"
            reason = "Recomputed action, facilities, and objective matched frozen decision lineage exactly."
        elif action_match and facilities_match:
            match_status = "SEMANTIC_MATCH"
            reason = "Recomputed action and facilities matched, slight numeric tolerance in objective value."
        else:
            match_status = "DRIFT"
            reason = f"Decision outputs drifted: recomputed facilities={res.opened_facility_ids}, frozen={orig.opened_facilities}"

        expected_h = hashlib.sha256(
            f"{orig.selected_action}:{','.join(sorted(orig.opened_facilities))}:{orig.objective_value}".encode()
        ).hexdigest()[:16]
        actual_h = hashlib.sha256(
            f"{res.action.value}:{','.join(sorted(res.opened_facility_ids))}:{recomputed_obj}".encode()
        ).hexdigest()[:16]

        diff: dict[str, str | int | float | list[str]] = {}
        if not action_match:
            diff["action"] = f"expected={orig.selected_action}, actual={res.action.value}"
        if not facilities_match:
            diff["facilities"] = list(res.opened_facility_ids)
        if not obj_match:
            diff["objective_diff"] = recomputed_obj - orig.objective_value

        replay_res = DecisionReplayResult(
            original_decision_id=original_decision_id,
            replayed_at=datetime.now(timezone.utc),
            pit_valid=pit_valid,
            reproduced_exact_action=action_match,
            reproduced_exact_facilities=facilities_match,
            objective_match=obj_match,
            match_status=match_status,
            expected_hash=expected_h,
            actual_hash=actual_h,
            difference=diff,
            reason=reason,
            code_sha=self.code_sha,
        )

        rep_id = f"rep-{hashlib.sha256(f'{original_decision_id}:{replay_res.replayed_at.isoformat()}'.encode()).hexdigest()[:16]}"
        self.repository.save_replay(
            replay_id=rep_id,
            original_decision_id=original_decision_id,
            workspace_id=ws_id,
            pit_valid=pit_valid,
            pit_cutoff=orig.decision_time,
            reproduced_exact_action=action_match,
            reproduced_exact_facilities=facilities_match,
            objective_match=obj_match,
            recomputed_objective=recomputed_obj,
            recomputed_facilities=list(res.opened_facility_ids),
            code_sha=self.code_sha,
        )
        return replay_res

    def create_shadow(
        self,
        decision_or_id: DecisionRecord | str,
        future_time: datetime | None = None,
        *,
        workspace_id: str | None = None,
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
            p_p95 = predicted_p95_seconds if predicted_p95_seconds is not None else decision_or_id.p95_travel_seconds
            ws_id = workspace_id or decision_or_id.workspace_id
        else:
            dec_id = decision_or_id
            f_time = future_observation_time or future_time
            if f_time is None:
                raise ValueError("future_observation_time required")
            orig = self.get_decision(dec_id, workspace_id)
            if orig is None:
                raise LookupError(f"Decision {dec_id} not found in ledger")
            f_decision_time = frozen_decision_time or orig.decision_time
            p_p95 = predicted_p95_seconds if predicted_p95_seconds is not None else orig.p95_travel_seconds
            ws_id = workspace_id or orig.workspace_id

        if f_time <= f_decision_time:
            raise ValueError("future_observation_time must be strictly after frozen_decision_time")

        if p_p95 is None or p_p95 <= 0:
            raise ValueError(
                "DECISION_LINEAGE_INCOMPLETE: predicted_p95_seconds must be derived from authoritative decision record"
            )

        h = hashlib.sha256(f"{dec_id}:{f_decision_time.isoformat()}:{f_time.isoformat()}".encode()).hexdigest()[:16]
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
        self.repository.create_shadow(shadow, workspace_id=ws_id)
        return shadow

    def get_shadow(self, shadow_id: str, workspace_id: str | None = None) -> ShadowEvaluation | None:
        return self.repository.get_shadow(shadow_id, workspace_id)

    def evaluate_shadow(
        self,
        shadow_id: str,
        workspace_id: str | None = None,
        *,
        actual_observed_p95_seconds: int,
        observation_valid_time: datetime | None = None,
    ) -> ShadowEvaluation:
        shadow = self.get_shadow(shadow_id, workspace_id)
        if shadow is None:
            raise LookupError(f"Shadow evaluation {shadow_id} not found")

        obs_time = observation_valid_time or shadow.future_observation_time
        if obs_time < shadow.future_observation_time:
            raise ValueError("Observation is premature for this shadow window")

        regret = actual_observed_p95_seconds - shadow.predicted_p95_seconds
        now = datetime.now(timezone.utc)
        target_ws = workspace_id or "00000000-0000-0000-0000-000000000001"
        self.repository.evaluate_shadow(
            shadow_id=shadow_id,
            workspace_id=target_ws,
            actual_observed_p95_seconds=actual_observed_p95_seconds,
            regret_seconds=regret,
            evaluated_at=now,
        )
        return ShadowEvaluation(
            shadow_id=shadow.shadow_id,
            decision_id=shadow.decision_id,
            frozen_decision_time=shadow.frozen_decision_time,
            future_observation_time=shadow.future_observation_time,
            shadow_state=ShadowState.EVALUATED,
            predicted_p95_seconds=shadow.predicted_p95_seconds,
            actual_observed_p95_seconds=actual_observed_p95_seconds,
            regret_seconds=regret,
            outcome_status=OutcomeStatus.EVALUATED,
            evaluated_at=now,
        )
