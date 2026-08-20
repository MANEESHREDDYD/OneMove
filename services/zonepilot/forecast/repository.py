"""PostgreSQL Repository for durable Forecast Records."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

import psycopg
from psycopg.rows import dict_row

from services.common.db_dsn import get_database_dsn
from services.zonepilot.forecast.contracts import PredictionRecord
from services.zonepilot.forecast.timeline import coerce_utc, utc_now

FORECAST_TABLE = "public.forecast_records"
ISSUE_TIME_COLUMN = "forecast_issue_time"
# Present on the temporal observation tables; forecast_records does not carry it
# today, so the predicate is added only when the column actually exists.
AVAILABILITY_COLUMN = "information_available_at"


def build_zone_forecast_pit_query(has_availability_column: bool) -> str:
    """Build the point-in-time forecast read.

    The previous query had no issue-time predicate at all and ordered by
    ``target_time DESC``, so ``limit=1`` returned the FURTHEST-FUTURE record --
    a forecast issued in the future was selectable from a past context (F-020).
    The read is now bounded by the decision time and ordered so that the row
    returned first is the LATEST forecast actually known at ``as_of``.
    """
    predicates = [
        "zone_id = %s",
        "workspace_id = %s",
        f"{ISSUE_TIME_COLUMN} <= %s",
    ]
    order_by = [f"{ISSUE_TIME_COLUMN} DESC", "target_time DESC"]
    if has_availability_column:
        predicates.append(f"{AVAILABILITY_COLUMN} <= %s")
        order_by.insert(0, f"{AVAILABILITY_COLUMN} DESC")
    return " ".join(
        [
            f"SELECT * FROM {FORECAST_TABLE}",
            "WHERE " + " AND ".join(predicates),
            "ORDER BY " + ", ".join(order_by),
            "LIMIT %s",
        ]
    )


def forecast_is_known_at(row: Mapping[str, Any], as_of: datetime) -> bool:
    """Was this forecast knowable at ``as_of``? Fail closed when it cannot be shown.

    Mirrors the SQL predicate as a defence in depth, so a row reaching the caller
    through any path (a cached read, a replayed fixture, a hand-built query)
    still cannot carry future information into a past context.
    """
    issued_at = coerce_utc(row.get(ISSUE_TIME_COLUMN))
    if issued_at is None or issued_at > as_of:
        return False
    if AVAILABILITY_COLUMN in row:
        # The column exists for this row, so a NULL/unparseable value is unknown
        # availability, which SQL would also exclude.
        available_at = coerce_utc(row.get(AVAILABILITY_COLUMN))
        if available_at is None or available_at > as_of:
            return False
    return True


class ForecastRepository:
    def __init__(self, dsn: str | None = None) -> None:
        self._explicit_dsn = dsn
        self._availability_column: bool | None = None

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

    def _has_availability_column(self, cur: Any) -> bool:
        """Detect the availability column once, so the predicate tracks the schema."""
        if self._availability_column is None:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'forecast_records'
                  AND column_name = %s
                """,
                [AVAILABILITY_COLUMN],
            )
            self._availability_column = cur.fetchone() is not None
        return self._availability_column

    def get_zone_forecasts_as_of(
        self,
        zone_id: str,
        workspace_id: str,
        as_of: datetime,
        limit: int = 24,
    ) -> list[dict[str, Any]]:
        """Fetch forecasts KNOWN AT ``as_of``, strictly scoped to the workspace.

        ``as_of`` is the decision time. A forecast issued after it did not exist
        for the caller's context and must not be selectable, however close its
        target time is (F-020).
        """
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("get_zone_forecasts_as_of requires a non-empty workspace_id")
        decision_time = coerce_utc(as_of)
        if decision_time is None:
            raise ValueError("get_zone_forecasts_as_of requires a datetime as_of")
        if limit is None or int(limit) < 1:
            raise ValueError("limit must be a positive integer")

        with self._connect() as conn:
            with conn.cursor() as cur:
                has_availability = self._has_availability_column(cur)
                params: list[Any] = [zone_id, workspace_id, decision_time]
                if has_availability:
                    params.append(decision_time)
                params.append(int(limit))
                cur.execute(build_zone_forecast_pit_query(has_availability), params)
                rows = cur.fetchall() or []

        return [dict(row) for row in rows if forecast_is_known_at(row, decision_time)]

    def get_zone_forecasts(
        self,
        zone_id: str,
        workspace_id: str,
        limit: int = 24,
        *,
        as_of: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Point-in-time forecast read; ``as_of`` defaults to now, never to unbounded.

        Callers that know their decision time should pass it (or call
        ``get_zone_forecasts_as_of`` directly). The default is deliberately the
        current instant rather than None, so an un-updated call site still cannot
        read a forecast issued in the future.
        """
        return self.get_zone_forecasts_as_of(
            zone_id,
            workspace_id,
            as_of if as_of is not None else utc_now(),
            limit,
        )
