"""One acquisition cycle: attempt every provider, record what happened either way.

This is the entrypoint that makes "live context" true rather than aspirational.
Before it existed, traffic and weather were fetched only when a demo page was
loaded, so `traffic_observations` and `weather_observations` held zero rows and
there was no history, no freshness guarantee, and nothing to replay against.

Three properties matter more than the fetching:

IDEMPOTENCY IS THE DATABASE'S JOB. Both observation tables carry a unique index
on (workspace_id, provider, zone_id, event_time, valid_at, issued_at). Re-running
a cycle inside the same provider interval conflicts and is skipped. Application-
side de-duplication would drift the moment two collectors ran at once.

A FAILURE IS A RECORD, NOT A GAP. If a provider cannot be reached, an outage row
is written naming the provider, a constrained reason code and the time of the
attempt. Absence of data must stay distinguishable from absence of congestion --
this is the same rule that makes UNAVAILABLE distinct from 0 everywhere else in
the system.

TIMESTAMPS DECLARE THEIR OWN PROVENANCE. Open-Meteo stamps its current block, so
that stamp is the event time and `event_time_source` says PROVIDER_SUPPLIED.
TomTom's flowSegmentData carries no observation time, so the fetch time stands in
and the column says FETCH_TIME_SUBSTITUTED. Publishing a fetch time as though a
provider had supplied it is a claim the system cannot support.

WHAT IS NOT STORED. No raw provider payload, no API key, no URL containing one.
The licence review found retention and redistribution concerns with keeping raw
third-party responses, so each row keeps normalized values plus a sha256 of the
response body and a request trace id -- enough to prove the acquisition happened
without retaining the restricted payload.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# The pilot workspace is resolved by SLUG, not by a hardcoded uuid. A literal id
# that does not exist in `workspaces` fails the foreign key at insert time, which
# is how this was first written and how it was caught; a slug is stable across
# environments and says what it means.
PILOT_WORKSPACE_SLUG = "bengaluru-pilot"

TOMTOM_PROVIDER = "TOMTOM"
OPEN_METEO_PROVIDER = "OPEN_METEO"

TOMTOM_FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

OPEN_METEO_CURRENT_FIELDS = (
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "rain",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "weather_code",
)

# Decision-relevant corridors, not an enormous bounding box. Each point is a real
# arterial in the pilot area; querying per corridor keeps provider usage
# proportionate to what the decision actually needs.
PILOT_CORRIDORS: tuple[tuple[str, float, float], ...] = (
    ("inner_ring_road_koramangala", 12.9348, 77.6200),
    ("hosur_road_silk_board", 12.9176, 77.6234),
    ("outer_ring_road_bellandur", 12.9300, 77.6740),
    ("hundred_feet_road_indiranagar", 12.9780, 77.6400),
    ("sarjapur_road_hsr", 12.9141, 77.6358),
    ("bannerghatta_road_jayanagar", 12.9250, 77.5938),
)

# Weather is sampled at a few defensible reference points rather than once per
# H3 cell: 94 identical requests would return the same regional model output and
# would be provider abuse for no additional information.
WEATHER_REFERENCE_POINTS: tuple[tuple[str, float, float], ...] = (
    ("blr_central", 12.9716, 77.5946),
    ("blr_south_east", 12.9165, 77.6500),
    ("blr_north", 13.0350, 77.5970),
)

_REASON_CODES = {
    "HTTP_ERROR",
    "TIMEOUT",
    "CONNECTION_FAILED",
    "AUTH_REJECTED",
    "RATE_LIMITED",
    "MALFORMED_RESPONSE",
    "NO_CREDENTIAL",
    "UNKNOWN",
}


@dataclass
class CaptureOutcome:
    """What one cycle actually did. Reported, not inferred."""

    capture_run_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None = None
    providers_attempted: list[str] = field(default_factory=list)
    providers_succeeded: list[str] = field(default_factory=list)
    providers_failed: list[str] = field(default_factory=list)
    observations_written: int = 0
    observations_skipped_as_duplicate: int = 0
    outages: list[tuple[str, str]] = field(default_factory=list)


def _tomtom_key() -> str | None:
    """Read the TomTom credential, never log or return it anywhere visible.

    The historical collector read TOMTOM_API_KEY, which is not the variable this
    deployment sets -- which is why the collectors had never once acquired. Both
    names are accepted so an existing deployment keeps working, but the value is
    never printed, hashed into an id, or written to a row.
    """
    for name in ("TOMTOM_API_KEY", "TOMTOM"):
        value = (os.environ.get(name) or "").strip()
        if value:
            return value

    # Fall back to the gitignored local env file, matching how the rest of the
    # local tooling resolves credentials.
    env_file = Path(os.environ.get("ONEMOVE_ENV_FILE", "OneMove.env"))
    if env_file.is_file():
        match = re.search(
            r"^\s*(?:TOMTOM_API_KEY|TOMTOM)\s*=\s*(\S+)",
            env_file.read_text(encoding="utf-8", errors="replace"),
            re.M,
        )
        if match:
            return match.group(1).strip().strip("\"'")
    return None


def _classify(exc: Exception) -> tuple[str, str]:
    """Map a failure onto the constrained reason codes the table accepts."""
    if isinstance(exc, httpx.TimeoutException):
        return "TIMEOUT", type(exc).__name__
    if isinstance(exc, httpx.ConnectError):
        return "CONNECTION_FAILED", type(exc).__name__
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in (401, 403):
            return "AUTH_REJECTED", f"HTTP {status}"
        if status == 429:
            return "RATE_LIMITED", f"HTTP {status}"
        return "HTTP_ERROR", f"HTTP {status}"
    if isinstance(exc, (KeyError, ValueError, json.JSONDecodeError)):
        return "MALFORMED_RESPONSE", type(exc).__name__
    return "UNKNOWN", type(exc).__name__


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _cell_for(lat: float, lon: float) -> str:
    import h3

    return h3.latlng_to_cell(lat, lon, 8)


# --- provider fetches --------------------------------------------------------


def fetch_traffic(client: httpx.Client, key: str) -> list[dict[str, Any]]:
    """Current flow on each pilot corridor. Raises on the first failure.

    Raising rather than partially succeeding is deliberate: a cycle that
    silently returned three of six corridors would leave the other three
    indistinguishable from corridors that are genuinely free-flowing.
    """
    readings: list[dict[str, Any]] = []
    for corridor_id, lat, lon in PILOT_CORRIDORS:
        response = client.get(
            TOMTOM_FLOW_URL,
            params={"key": key, "point": f"{lat},{lon}", "unit": "KMPH"},
            timeout=20.0,
        )
        response.raise_for_status()
        segment = response.json()["flowSegmentData"]

        current_speed = float(segment["currentSpeed"])
        free_flow_speed = float(segment["freeFlowSpeed"])
        readings.append(
            {
                "corridor_id": corridor_id,
                "zone_id": _cell_for(lat, lon),
                "current_speed_kmph": current_speed,
                "free_flow_speed_kmph": free_flow_speed,
                "current_travel_time_s": int(segment["currentTravelTime"]),
                "free_flow_travel_time_s": int(segment["freeFlowTravelTime"]),
                # 1.0 means free-flowing; above 1.0 means slower than free flow.
                "congestion_ratio": (free_flow_speed / current_speed) if current_speed > 0 else None,
                "confidence": segment.get("confidence"),
                "road_class": segment.get("frc"),
                "response_sha256": _digest(response.content),
                "request_trace_id": response.headers.get("x-request-id") or response.headers.get("tracking-id"),
            }
        )
    return readings


def fetch_weather(client: httpx.Client) -> list[dict[str, Any]]:
    """Current model state at each reference point, with its own timestamp."""
    readings: list[dict[str, Any]] = []
    for point_id, lat, lon in WEATHER_REFERENCE_POINTS:
        response = client.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": ",".join(OPEN_METEO_CURRENT_FIELDS),
                "timezone": "UTC",
            },
            timeout=20.0,
            headers={"User-Agent": "OneMove/1.0 (pilot data acquisition)"},
        )
        response.raise_for_status()
        body = response.json()
        current = body["current"]

        # Open-Meteo stamps the block it is reporting. That is the event time.
        provider_time = datetime.fromisoformat(current["time"]).replace(tzinfo=timezone.utc)

        readings.append(
            {
                "point_id": point_id,
                "zone_id": _cell_for(lat, lon),
                # Only values the provider actually returned. A field absent from
                # the response stays absent rather than becoming a plausible zero.
                "values": {name: current[name] for name in OPEN_METEO_CURRENT_FIELDS if name in current},
                "units": body.get("current_units", {}),
                "provider_event_time": provider_time,
                "model": body.get("model") or "open-meteo-best-match",
                "response_sha256": _digest(response.content),
                "request_trace_id": response.headers.get("x-request-id"),
            }
        )
    return readings


# --- persistence -------------------------------------------------------------


def resolve_workspace(conn, slug: str = PILOT_WORKSPACE_SLUG) -> uuid.UUID:
    """The workspace id for a slug, or a loud failure.

    Refusing to invent one matters: an unknown workspace would either violate the
    foreign key or, worse, silently write the pilot's observations into a
    workspace nobody reads.
    """
    row = conn.execute("select id from public.workspaces where slug = %s", (slug,)).fetchone()
    if row is None:
        known = [r[0] for r in conn.execute("select slug from public.workspaces order by slug").fetchall()]
        raise LookupError(f"no workspace with slug {slug!r}; known slugs are {known}")
    return row[0]


def _open_connection():
    import psycopg

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set; refusing to guess a database")
    return psycopg.connect(dsn, autocommit=False)


def run_capture_cycle(
    *,
    candidate_sha: str,
    environment: str,
    workspace_id: uuid.UUID | None = None,
    dataset_version: str = "r1-pilot",
    now: datetime | None = None,
) -> CaptureOutcome:
    """Attempt both providers once and record the cycle, whatever happened."""
    started = now or datetime.now(timezone.utc)
    outcome = CaptureOutcome(capture_run_id=uuid.uuid4(), started_at=started)

    with _open_connection() as conn:
        if workspace_id is None:
            workspace_id = resolve_workspace(conn)
        conn.execute(
            """insert into public.provider_capture_runs
                   (capture_run_id, workspace_id, started_at, candidate_sha, environment,
                    providers_attempted)
               values (%s, %s, %s, %s, %s, %s)""",
            (outcome.capture_run_id, workspace_id, started, candidate_sha, environment,
             [TOMTOM_PROVIDER, OPEN_METEO_PROVIDER]),
        )
        outcome.providers_attempted = [TOMTOM_PROVIDER, OPEN_METEO_PROVIDER]
        conn.commit()

        # try/finally, because a run row left without completed_at is worse than
        # a recorded failure: it reads as a cycle still in flight forever. The
        # first execution of this module produced exactly that -- a foreign key
        # violation escaped mid-cycle and left an orphan run with no outcome and
        # no outage. Whatever happens, the run is closed out.
        try:
            with httpx.Client() as client:
                _capture_traffic(conn, client, outcome, workspace_id, dataset_version)
                _capture_weather(conn, client, outcome, workspace_id, dataset_version)
        finally:
            outcome.completed_at = datetime.now(timezone.utc)
            # Any provider that neither succeeded nor recorded an outage was cut
            # short by something outside the per-provider handlers. Mark it
            # failed rather than leaving it looking un-attempted.
            for provider in outcome.providers_attempted:
                if provider not in outcome.providers_succeeded and provider not in outcome.providers_failed:
                    outcome.providers_failed.append(provider)
            # The per-provider handlers commit their own work, so anything still
            # open here is a failed statement's aborted transaction. Roll it back
            # so the closing update can run at all.
            conn.rollback()
            _finalize_run(conn, outcome)

    return outcome


def _finalize_run(conn, outcome: CaptureOutcome) -> None:
    """Write the cycle's outcome. Runs on every path, including the failing one."""
    conn.execute(
        """update public.provider_capture_runs
              set completed_at = %s,
                  providers_succeeded = %s,
                  providers_failed = %s,
                  observation_count = %s
            where capture_run_id = %s""",
        (outcome.completed_at, outcome.providers_succeeded, outcome.providers_failed,
         outcome.observations_written, outcome.capture_run_id),
    )
    conn.commit()


def _record_outage(conn, outcome: CaptureOutcome, workspace_id: uuid.UUID, provider: str,
                   reason_code: str, detail: str) -> None:
    assert reason_code in _REASON_CODES, f"unknown reason code {reason_code}"
    last_success = conn.execute(
        """select max(retrieved_at) from public.traffic_observations where provider = %s and workspace_id = %s"""
        if provider == TOMTOM_PROVIDER
        else """select max(retrieved_at) from public.weather_observations where provider = %s and workspace_id = %s""",
        (provider, workspace_id),
    ).fetchone()[0]

    conn.execute(
        """insert into public.provider_outages
               (workspace_id, capture_run_id, provider, reason_code, detail, attempted_at, last_success_at)
           values (%s, %s, %s, %s, %s, %s, %s)
           on conflict (capture_run_id, provider) do nothing""",
        (workspace_id, outcome.capture_run_id, provider, reason_code, detail[:500],
         datetime.now(timezone.utc), last_success),
    )
    conn.commit()
    outcome.providers_failed.append(provider)
    outcome.outages.append((provider, reason_code))


def _capture_traffic(conn, client, outcome, workspace_id, dataset_version) -> None:
    key = _tomtom_key()
    if not key:
        _record_outage(conn, outcome, workspace_id, TOMTOM_PROVIDER, "NO_CREDENTIAL",
                       "no TomTom credential resolved from TOMTOM_API_KEY, TOMTOM, or the env file")
        return

    try:
        readings = fetch_traffic(client, key)
    except Exception as exc:  # noqa: BLE001 - every failure must become a record
        reason, detail = _classify(exc)
        _record_outage(conn, outcome, workspace_id, TOMTOM_PROVIDER, reason, detail)
        return

    retrieved = datetime.now(timezone.utc)
    written = 0
    for reading in readings:
        # flowSegmentData carries no observation time, so the fetch time stands
        # in and the row says so.
        cursor = conn.execute(
            """insert into public.traffic_observations
                   (run_id, workspace_id, zone_id, provider, provider_version, congestion_level,
                    observed_at, event_time, issued_at, valid_at, retrieved_at,
                    information_available_at, evidence_class, dataset_version,
                    request_trace_id, response_sha256, event_time_source)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       'PROVIDER_ESTIMATED', %s, %s, %s, 'FETCH_TIME_SUBSTITUTED')
               on conflict do nothing""",
            (outcome.capture_run_id, workspace_id, reading["zone_id"], TOMTOM_PROVIDER,
             "flowSegmentData/absolute/10", reading["congestion_ratio"],
             retrieved, retrieved, retrieved, retrieved, retrieved, retrieved,
             dataset_version, reading["request_trace_id"], reading["response_sha256"]),
        )
        if cursor.rowcount:
            written += 1
        else:
            outcome.observations_skipped_as_duplicate += 1
    conn.commit()

    outcome.observations_written += written
    outcome.providers_succeeded.append(TOMTOM_PROVIDER)


def _capture_weather(conn, client, outcome, workspace_id, dataset_version) -> None:
    try:
        readings = fetch_weather(client)
    except Exception as exc:  # noqa: BLE001 - every failure must become a record
        reason, detail = _classify(exc)
        _record_outage(conn, outcome, workspace_id, OPEN_METEO_PROVIDER, reason, detail)
        return

    retrieved = datetime.now(timezone.utc)
    written = 0
    for reading in readings:
        event_time = reading["provider_event_time"]
        values = reading["values"]
        cursor = conn.execute(
            """insert into public.weather_observations
                   (run_id, workspace_id, zone_id, provider, provider_version,
                    temperature, precipitation,
                    observed_at, event_time, issued_at, valid_at, retrieved_at,
                    information_available_at, evidence_class, dataset_version,
                    request_trace_id, response_sha256, event_time_source)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       'PUBLIC_OFFICIAL', %s, %s, %s, 'PROVIDER_SUPPLIED')
               on conflict do nothing""",
            (outcome.capture_run_id, workspace_id, reading["zone_id"], OPEN_METEO_PROVIDER,
             reading["model"], values.get("temperature_2m"), values.get("precipitation"),
             event_time, event_time, event_time, event_time, retrieved, retrieved,
             dataset_version, reading["request_trace_id"], reading["response_sha256"]),
        )
        if cursor.rowcount:
            written += 1
        else:
            outcome.observations_skipped_as_duplicate += 1
    conn.commit()

    outcome.observations_written += written
    outcome.providers_succeeded.append(OPEN_METEO_PROVIDER)
