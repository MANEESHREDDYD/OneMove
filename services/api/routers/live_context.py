"""What the system currently knows, and how sure it is of each part.

The product's central claim is that a reader never has to guess which parts of
the picture are real. This endpoint is where that claim is served from: one
response naming every source, its provider, its evidence class, when it was
captured, how old that is, and whether it is still fresh enough to describe the
present.

WHY THE BROWSER MUST NOT DO THIS ITSELF. Calling TomTom and Open-Meteo from
client code would leak the credential into the page, multiply provider cost by
the number of viewers, and give each viewer a different freshness answer for the
same moment. Acquisition happens once, server-side, into a normalized temporal
store; this endpoint reads that store.

THE HARD RULE. A source with no observation is UNAVAILABLE with a null age.
Never zero congestion, never zero rainfall, never a plausible substitute, and
never the word LIVE over a reading that is hours old. Absence of data and
absence of congestion are different facts and the response keeps them apart.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import psycopg
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from services.api.core.auth import get_current_user
from services.api.routers.observatory import standard_error
from services.zonepilot.dataquality.capture import (
    OPEN_METEO_PROVIDER,
    PILOT_WORKSPACE_SLUG,
    TOMTOM_PROVIDER,
)
from services.zonepilot.dataquality.freshness import FreshnessState, assess, policy_for

router = APIRouter(prefix="/api/v1/demo", tags=["live-context"])
logger = logging.getLogger("zonepilot.live_context")


class SourceContext(BaseModel):
    """One source's current standing. Every field is answerable or explicitly null."""

    source: str
    provider: str | None
    evidence_class: str
    freshness: str
    captured_at: datetime | None
    age_seconds: int | None
    observation_count: int
    detail: str | None = None
    # Only populated where the source has one; a count of zero is a real zero,
    # whereas a missing observation is expressed by freshness = UNAVAILABLE.
    failure_count: int = 0
    last_failure_at: datetime | None = None
    last_failure_reason: str | None = None


class ZoneTraffic(BaseModel):
    """Congestion per H3 zone. `congestion_ratio` is null when unknown, never 0."""

    zone_id: str
    congestion_ratio: float | None
    evidence_class: str = "PROVIDER_ESTIMATED"
    captured_at: datetime | None


class LiveContextResponse(BaseModel):
    as_of: datetime
    capture_run_id: str | None
    sources: list[SourceContext]
    zone_traffic: list[ZoneTraffic] = Field(default_factory=list)


def _connect():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        standard_error(
            "DEPENDENCY_UNAVAILABLE",
            "The observation store is not configured.",
            503,
        )
    return psycopg.connect(dsn)


def _observation_context(
    conn, workspace_id, table: str, provider: str, source_name: str, evidence_class: str
) -> SourceContext:
    """Grade one provider's most recent observation, or report its absence."""
    row = conn.execute(
        f"""select max(event_time), count(*)
              from public.{table}
             where workspace_id = %s and provider = %s""",  # noqa: S608 - table is a literal
        (workspace_id, provider),
    ).fetchone()
    latest, count = (row or (None, 0))

    failure = conn.execute(
        """select count(*), max(attempted_at)
             from public.provider_outages
            where workspace_id = %s and provider = %s""",
        (workspace_id, provider),
    ).fetchone()
    failure_count, last_failure = (failure or (0, None))

    last_reason = None
    if last_failure is not None:
        reason_row = conn.execute(
            """select reason_code from public.provider_outages
                where workspace_id = %s and provider = %s
                order by attempted_at desc limit 1""",
            (workspace_id, provider),
        ).fetchone()
        last_reason = reason_row[0] if reason_row else None

    verdict = assess(provider, latest)
    policy = policy_for(provider)

    detail = None
    if verdict.state is FreshnessState.UNAVAILABLE:
        detail = "No observation has been recorded for this provider."
    elif verdict.state is FreshnessState.STALE:
        # The last known reading may still be shown, but never as current.
        detail = (
            f"Last known reading, {verdict.age_seconds}s old. Beyond the "
            f"{int(policy.degraded_within.total_seconds())}s window this provider is expected to "
            "refresh within, so it is not current."
        )

    return SourceContext(
        source=source_name,
        provider=provider,
        evidence_class=evidence_class,
        freshness=verdict.state.value,
        captured_at=verdict.observed_at,
        age_seconds=verdict.age_seconds,
        observation_count=int(count or 0),
        detail=detail,
        failure_count=int(failure_count or 0),
        last_failure_at=last_failure,
        last_failure_reason=last_reason,
    )


@router.get("/live-context", response_model=LiveContextResponse)
def get_live_context(_user: dict = Depends(get_current_user)) -> LiveContextResponse:
    """Every source the demo displays, with its provenance and its freshness."""
    now = datetime.now(timezone.utc)

    try:
        with _connect() as conn:
            workspace = conn.execute(
                "select id from public.workspaces where slug = %s", (PILOT_WORKSPACE_SLUG,)
            ).fetchone()
            if workspace is None:
                standard_error(
                    "WORKSPACE_NOT_FOUND",
                    f"No workspace with slug {PILOT_WORKSPACE_SLUG!r}.",
                    404,
                )
            workspace_id = workspace[0]

            sources = [
                _observation_context(
                    conn, workspace_id, "traffic_observations", TOMTOM_PROVIDER,
                    "Traffic", "PROVIDER_ESTIMATED",
                ),
                _observation_context(
                    conn, workspace_id, "weather_observations", OPEN_METEO_PROVIDER,
                    "Weather", "PUBLIC_OFFICIAL",
                ),
            ]

            run = conn.execute(
                """select capture_run_id from public.provider_capture_runs
                    where workspace_id = %s and completed_at is not null
                    order by started_at desc limit 1""",
                (workspace_id,),
            ).fetchone()

            # The most recent reading per zone. Older rows for the same zone are
            # history, not competing answers.
            zone_rows = conn.execute(
                """select distinct on (zone_id) zone_id, congestion_level, event_time
                     from public.traffic_observations
                    where workspace_id = %s and provider = %s
                    order by zone_id, event_time desc""",
                (workspace_id, TOMTOM_PROVIDER),
            ).fetchall()
    except psycopg.Error as exc:
        logger.warning("live_context_store_unavailable", extra={"detail": str(exc)})
        standard_error(
            "DEPENDENCY_UNAVAILABLE",
            "The observation store could not be read, so no context can be reported. "
            "No values are substituted.",
            503,
        )

    traffic_fresh = sources[0].freshness in (FreshnessState.FRESH.value, FreshnessState.DEGRADED.value)

    return LiveContextResponse(
        as_of=now,
        capture_run_id=str(run[0]) if run else None,
        sources=[
            *sources,
            SourceContext(
                source="Network geography",
                provider=None,
                evidence_class="PUBLIC_GEOGRAPHIC",
                # Geography does not go stale on a provider cadence; it changes
                # when the extract is recut. Reporting it as FRESH on a clock
                # would be a category error, so it is reported as what it is.
                freshness="VERSIONED",
                captured_at=None,
                age_seconds=None,
                observation_count=94,
                detail="94 H3 resolution-8 cells from pilot_roads.osm.pbf.",
            ),
            SourceContext(
                source="Delivery mission",
                provider=None,
                evidence_class="SIMULATED",
                freshness="VERSIONED",
                captured_at=None,
                age_seconds=None,
                observation_count=16,
                detail="16 simulated orders on real coordinates. No customer, merchant or rider.",
            ),
        ],
        zone_traffic=[
            ZoneTraffic(
                zone_id=zone_id,
                # A stale reading must not be served as the current state of a
                # zone. The row still exists in history; it is simply not an
                # answer to "what is happening now".
                congestion_ratio=(float(ratio) if ratio is not None and traffic_fresh else None),
                captured_at=event_time,
            )
            for zone_id, ratio, event_time in zone_rows
        ],
    )
