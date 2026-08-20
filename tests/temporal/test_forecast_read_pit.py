"""F-020 (reopened), path (b): the forecast read had no issue-time bound at all.

``get_zone_forecasts`` selected by zone and workspace and ordered by
``target_time DESC``, so ``limit=1`` returned the FURTHEST-FUTURE record. The
Assistant consumes exactly that row, which made a forecast issued in the future
selectable from a past context.

These tests need no database. A fake cursor executes the SQL the repository
actually builds by reading the predicates out of the emitted statement, so a
dropped predicate or a reordered parameter list fails here rather than silently
widening the query.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from services.zonepilot.assistant.contracts import AssistantToolCall, ToolName
from services.zonepilot.assistant.tools import build_assistant_registry
from services.zonepilot.forecast.repository import (
    AVAILABILITY_COLUMN,
    ISSUE_TIME_COLUMN,
    ForecastRepository,
    build_zone_forecast_pit_query,
    forecast_is_known_at,
)

TODAY = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
ZONE = "8860145b59fffff"
WS = "ws-pit-test"


def _row(
    forecast_id: str,
    *,
    issued: datetime,
    target: datetime,
    available: datetime | None = None,
    zone_id: str = ZONE,
    workspace_id: str = WS,
    predicted_value: float = 1.0,
) -> dict[str, Any]:
    row = {
        "forecast_id": forecast_id,
        "zone_id": zone_id,
        "workspace_id": workspace_id,
        "target_metric": "HOURLY_PRECIPITATION_MM",
        ISSUE_TIME_COLUMN: issued,
        "target_time": target,
        "predicted_value": predicted_value,
    }
    if available is not None:
        row[AVAILABILITY_COLUMN] = available
    return row


class _FakeCursor:
    """Executes the emitted SQL by interpreting the predicates it contains.

    Deliberately not a stub that returns a canned list: the assertions below are
    only meaningful if a repository that stopped filtering would actually return
    the leaking row.
    """

    def __init__(self, rows: list[dict[str, Any]], has_availability_column: bool, statements: list[str]) -> None:
        self._rows = rows
        self._has_availability_column = has_availability_column
        self._statements = statements
        self._result: list[dict[str, Any]] = []

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._statements.append(sql)
        if "information_schema.columns" in sql:
            self._result = [{"exists": 1}] if self._has_availability_column else []
            return
        self._result = self._select(sql, list(params or []))

    def _select(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        assert f"{ISSUE_TIME_COLUMN} <= %s" in sql, "the read has no issue-time bound"
        zone_id, workspace_id, issue_bound = params[0], params[1], params[2]
        index = 3
        availability_bound = None
        if f"{AVAILABILITY_COLUMN} <= %s" in sql:
            availability_bound = params[index]
            index += 1
        limit = params[index]

        selected = [
            row
            for row in self._rows
            if row["zone_id"] == zone_id
            and row["workspace_id"] == workspace_id
            and row[ISSUE_TIME_COLUMN] <= issue_bound
        ]
        if availability_bound is not None:
            selected = [
                row
                for row in selected
                if row.get(AVAILABILITY_COLUMN) is not None and row[AVAILABILITY_COLUMN] <= availability_bound
            ]
            selected.sort(
                key=lambda row: (row[AVAILABILITY_COLUMN], row[ISSUE_TIME_COLUMN], row["target_time"]),
                reverse=True,
            )
        else:
            selected.sort(key=lambda row: (row[ISSUE_TIME_COLUMN], row["target_time"]), reverse=True)
        return selected[:limit]

    def fetchall(self) -> list[dict[str, Any]]:
        return self._result

    def fetchone(self) -> dict[str, Any] | None:
        return self._result[0] if self._result else None


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        return None

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        return None


def _repository(
    rows: list[dict[str, Any]],
    *,
    has_availability_column: bool = False,
) -> tuple[ForecastRepository, list[str]]:
    statements: list[str] = []
    cursor = _FakeCursor(rows, has_availability_column, statements)
    repo = ForecastRepository(dsn="postgresql://unused/never-connected")
    repo._connect = lambda: _FakeConnection(cursor)  # type: ignore[method-assign]
    return repo, statements


# --- the three adversarial cases ------------------------------------------


def test_forecast_issued_tomorrow_is_excluded_from_a_decision_today() -> None:
    """target tomorrow / issued tomorrow / decision today -> EXCLUDED."""
    repo, _ = _repository([_row("f-future", issued=TOMORROW, target=TOMORROW + timedelta(hours=1))])

    assert repo.get_zone_forecasts_as_of(ZONE, WS, TODAY) == []


def test_forecast_issued_yesterday_for_tomorrow_is_eligible_today() -> None:
    """target tomorrow / issued yesterday / decision today -> ELIGIBLE."""
    repo, _ = _repository([_row("f-known", issued=YESTERDAY, target=TOMORROW)])

    rows = repo.get_zone_forecasts_as_of(ZONE, WS, TODAY)

    assert [row["forecast_id"] for row in rows] == ["f-known"]


def test_record_available_only_tomorrow_is_excluded_from_a_decision_today() -> None:
    """event yesterday but available tomorrow / decision today -> EXCLUDED."""
    repo, _ = _repository(
        [
            _row("f-late", issued=YESTERDAY, target=TODAY, available=TOMORROW),
            _row("f-known", issued=YESTERDAY, target=TODAY, available=YESTERDAY),
        ],
        has_availability_column=True,
    )

    rows = repo.get_zone_forecasts_as_of(ZONE, WS, TODAY)

    assert [row["forecast_id"] for row in rows] == ["f-known"]


# --- ordering: latest KNOWN, not furthest target --------------------------


def test_limit_one_returns_the_latest_known_forecast_not_the_furthest_target() -> None:
    """ORDER BY target_time DESC made limit=1 the furthest-future record."""
    repo, _ = _repository(
        [
            _row("f-stale-but-distant", issued=YESTERDAY, target=TODAY + timedelta(days=5)),
            _row("f-freshest", issued=TODAY - timedelta(hours=1), target=TODAY + timedelta(hours=1)),
        ]
    )

    rows = repo.get_zone_forecasts_as_of(ZONE, WS, TODAY, limit=1)

    assert [row["forecast_id"] for row in rows] == ["f-freshest"]


def test_query_does_not_order_by_target_time_first() -> None:
    for has_availability in (False, True):
        sql = build_zone_forecast_pit_query(has_availability)
        order_by = sql.split("ORDER BY", 1)[1]
        assert not order_by.strip().startswith("target_time"), sql
        assert f"{ISSUE_TIME_COLUMN} <= %s" in sql
        assert (f"{AVAILABILITY_COLUMN} <= %s" in sql) is has_availability


# --- defaults, scoping and fail-closed behaviour --------------------------


def test_the_default_as_of_still_excludes_a_future_issued_forecast() -> None:
    """The unedited router call site must not be able to read the future."""
    repo, _ = _repository(
        [
            _row("f-future", issued=TOMORROW, target=TOMORROW),
            _row("f-known", issued=YESTERDAY, target=TOMORROW),
        ]
    )

    rows = repo.get_zone_forecasts(ZONE, WS)

    assert [row["forecast_id"] for row in rows] == ["f-known"]


def test_another_workspace_cannot_be_read() -> None:
    repo, _ = _repository([_row("f-other", issued=YESTERDAY, target=TOMORROW, workspace_id="ws-other")])

    assert repo.get_zone_forecasts_as_of(ZONE, WS, TODAY) == []


@pytest.mark.parametrize("workspace_id", ["", "   "])
def test_a_blank_workspace_is_rejected(workspace_id: str) -> None:
    repo, _ = _repository([])

    with pytest.raises(ValueError):
        repo.get_zone_forecasts_as_of(ZONE, workspace_id, TODAY)


def test_a_missing_as_of_is_rejected_rather_than_defaulted_inside_the_pit_read() -> None:
    repo, _ = _repository([])

    with pytest.raises(ValueError):
        repo.get_zone_forecasts_as_of(ZONE, WS, "not-a-timestamp")  # type: ignore[arg-type]


def test_rows_are_filtered_again_in_python_when_the_query_does_not_filter() -> None:
    """Defence in depth: a leaking row must not survive a permissive read path."""

    class _HostileCursor(_FakeCursor):
        def _select(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
            return list(self._rows)

    statements: list[str] = []
    cursor = _HostileCursor(
        [
            _row("f-future", issued=TOMORROW, target=TOMORROW),
            _row("f-known", issued=YESTERDAY, target=TOMORROW),
        ],
        False,
        statements,
    )
    repo = ForecastRepository(dsn="postgresql://unused/never-connected")
    repo._connect = lambda: _FakeConnection(cursor)  # type: ignore[method-assign]

    rows = repo.get_zone_forecasts_as_of(ZONE, WS, TODAY)

    assert [row["forecast_id"] for row in rows] == ["f-known"]


def test_forecast_is_known_at_fails_closed() -> None:
    assert forecast_is_known_at({ISSUE_TIME_COLUMN: YESTERDAY}, TODAY) is True
    assert forecast_is_known_at({ISSUE_TIME_COLUMN: TOMORROW}, TODAY) is False
    # Exactly at the decision time: knowable.
    assert forecast_is_known_at({ISSUE_TIME_COLUMN: TODAY}, TODAY) is True
    # No issue time at all -- it cannot be shown to have existed.
    assert forecast_is_known_at({}, TODAY) is False
    assert forecast_is_known_at({ISSUE_TIME_COLUMN: None}, TODAY) is False
    # The availability column exists but is NULL: unknown availability.
    assert forecast_is_known_at({ISSUE_TIME_COLUMN: YESTERDAY, AVAILABILITY_COLUMN: None}, TODAY) is False
    assert forecast_is_known_at({ISSUE_TIME_COLUMN: YESTERDAY, AVAILABILITY_COLUMN: TOMORROW}, TODAY) is False
    assert forecast_is_known_at({ISSUE_TIME_COLUMN: YESTERDAY, AVAILABILITY_COLUMN: YESTERDAY}, TODAY) is True
    # ISO strings from a JSON-ish row are honoured, not treated as absent.
    assert forecast_is_known_at({ISSUE_TIME_COLUMN: YESTERDAY.isoformat()}, TODAY) is True


# --- the Assistant consumes the point-in-time read ------------------------


class _RecordingRepository:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[tuple[Any, ...]] = []

    def get_zone_forecasts_as_of(self, zone_id, workspace_id, as_of, limit=24):
        self.calls.append((zone_id, workspace_id, as_of, limit))
        return [row for row in self.rows if forecast_is_known_at(row, as_of)][:limit]


class _UnboundedRepository:
    """A repository that only offers the leaking, unbounded read."""

    def get_zone_forecasts(self, zone_id, workspace_id, limit=1):
        return [_row("f-future", issued=TOMORROW, target=TOMORROW)]


def _assistant(repository: Any):
    return build_assistant_registry(
        observatory_service=object(),
        decision_ledger=object(),
        forecast_repository=repository,
    )


def _call(repository: Any, arguments: dict[str, Any]):
    return _assistant(repository).execute(
        AssistantToolCall(tool_name=ToolName.GET_FORECAST, arguments=arguments, workspace_id=WS)
    )


def test_assistant_reads_at_an_explicit_decision_time() -> None:
    repo = _RecordingRepository(
        [
            _row("f-future", issued=TOMORROW, target=TOMORROW),
            _row("f-known", issued=YESTERDAY, target=TOMORROW),
        ]
    )

    result = _call(repo, {"zone_id": ZONE, "as_of": TODAY.isoformat()})

    assert result.success is True, result.error_message
    assert result.result_data["record_id"] == "f-known"
    assert result.result_data["as_of"] == TODAY.isoformat()
    assert repo.calls == [(ZONE, WS, TODAY, 1)]


def test_assistant_defaults_to_now_and_cannot_see_a_future_forecast() -> None:
    repo = _RecordingRepository([_row("f-future", issued=TOMORROW, target=TOMORROW)])

    result = _call(repo, {"zone_id": ZONE})

    assert result.success is False
    assert result.result_data == {"status": "UNAVAILABLE"}
    assert "UNAVAILABLE" in (result.error_message or "")


def test_assistant_refuses_a_repository_without_a_point_in_time_read() -> None:
    """No silent fallback to the unbounded read that caused the leak."""
    result = _call(_UnboundedRepository(), {"zone_id": ZONE})

    assert result.success is False
    assert result.result_data == {"status": "UNAVAILABLE"}
    assert "point-in-time" in (result.error_message or "")


def test_assistant_rejects_an_unparseable_decision_time() -> None:
    repo = _RecordingRepository([_row("f-known", issued=YESTERDAY, target=TOMORROW)])

    result = _call(repo, {"zone_id": ZONE, "as_of": "yesterday-ish"})

    assert result.success is False
    assert repo.calls == [], "an unparseable as_of must not fall back to an unbounded now"
