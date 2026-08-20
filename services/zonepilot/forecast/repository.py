"""PostgreSQL Repository for durable Forecast Records."""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from services.common.db_dsn import get_database_dsn
from services.zonepilot.forecast.contracts import PredictionRecord


class ForecastRepository:
    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or get_database_dsn()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=15)

    def save_prediction(self, record: PredictionRecord) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.forecast_records (
                        forecast_id, workspace_id, zone_id, target_metric,
                        forecast_issue_time, horizon_hours, target_time, predicted_value,
                        baseline_model, model_version, feature_dataset_version, graph_version,
                        code_sha, lower_bound, upper_bound, evidence_ids
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON CONFLICT (forecast_id) DO UPDATE SET
                        predicted_value = EXCLUDED.predicted_value
                    """,
                    (
                        record.prediction_id,
                        record.workspace_id,
                        record.zone_id,
                        record.target.value,
                        record.prediction_time,
                        record.horizon_hours,
                        record.target_time,
                        record.predicted_value,
                        record.baseline_model.value,
                        record.model_version,
                        record.dataset_version,
                        record.graph_version,
                        record.code_sha,
                        record.lower_bound,
                        record.upper_bound,
                        list(record.evidence_ids),
                    ),
                )
            conn.commit()

    def get_zone_forecasts(self, zone_id: str, workspace_id: str, limit: int = 24) -> list[dict[str, Any]]:
        """Fetch persisted forecasts for a zone, strictly scoped to the workspace."""
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("get_zone_forecasts requires a non-empty workspace_id")

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM public.forecast_records
                    WHERE zone_id = %s AND workspace_id = %s
                    ORDER BY target_time DESC LIMIT %s
                    """,
                    [zone_id, workspace_id, limit],
                )
                return cur.fetchall()
