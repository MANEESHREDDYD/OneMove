"""Acquisition must be idempotent, and a failure must leave a record.

These tests use stubs rather than live providers. Proving the failure path by
actually breaking TomTom would mean manufacturing load on a third party to
watch it fail, and proving idempotency by hammering it would be worse. The live
path was exercised separately -- five real cycles, one induced failure and a
recovery -- and that evidence is recorded in the commit rather than re-run here.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from services.zonepilot.dataquality import capture

# --- what the collector refuses to invent ------------------------------------


def test_every_failure_maps_onto_a_reason_code_the_table_accepts() -> None:
    """A reason code the CHECK constraint rejects would abort the outage insert,
    turning a recorded failure back into a silent gap."""
    request = httpx.Request("GET", "https://example.invalid/x")

    cases = [
        (httpx.ConnectTimeout("slow", request=request), "TIMEOUT"),
        (httpx.ConnectError("refused", request=request), "CONNECTION_FAILED"),
        (httpx.HTTPStatusError("", request=request, response=httpx.Response(401, request=request)), "AUTH_REJECTED"),
        (httpx.HTTPStatusError("", request=request, response=httpx.Response(403, request=request)), "AUTH_REJECTED"),
        (httpx.HTTPStatusError("", request=request, response=httpx.Response(429, request=request)), "RATE_LIMITED"),
        (httpx.HTTPStatusError("", request=request, response=httpx.Response(500, request=request)), "HTTP_ERROR"),
        (KeyError("flowSegmentData"), "MALFORMED_RESPONSE"),
        (json.JSONDecodeError("bad", "", 0), "MALFORMED_RESPONSE"),
        (RuntimeError("something else"), "UNKNOWN"),
    ]

    for exc, expected in cases:
        reason, detail = capture._classify(exc)
        assert reason == expected, f"{type(exc).__name__} classified as {reason}"
        assert reason in capture._REASON_CODES
        assert detail, "an outage must carry a detail, not just a code"


def test_a_partial_traffic_cycle_raises_rather_than_returning_half() -> None:
    """Three of six corridors returned silently would leave the other three
    indistinguishable from corridors that are genuinely free-flowing."""
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] <= 2:
            return httpx.Response(
                200,
                json={
                    "flowSegmentData": {
                        "currentSpeed": 20,
                        "freeFlowSpeed": 40,
                        "currentTravelTime": 100,
                        "freeFlowTravelTime": 50,
                        "confidence": 1,
                        "frc": "FRC2",
                    }
                },
            )
        return httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            capture.fetch_traffic(client, key="stub-not-a-real-key")

    assert calls["n"] == 3, "it must stop at the first failure, not push on"


def test_weather_keeps_only_fields_the_provider_actually_returned() -> None:
    """A field absent from the response must stay absent, not become a zero.

    A missing precipitation reading rendered as 0.0 mm is the exact confusion
    between UNAVAILABLE and zero that this system exists to avoid.
    """
    partial = {
        "current": {
            "time": "2026-08-25T14:45",
            "temperature_2m": 23.2,
            "precipitation": 0.0,
            # wind, humidity, weather_code deliberately absent
        },
        "current_units": {"temperature_2m": "C"},
    }

    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=partial))) as client:
        readings = capture.fetch_weather(client)

    values = readings[0]["values"]
    assert set(values) == {"temperature_2m", "precipitation"}
    for absent in ("wind_speed_10m", "relative_humidity_2m", "weather_code"):
        assert absent not in values, f"{absent} was not returned and must not be materialised"


def test_the_provider_timestamp_is_used_when_the_provider_supplies_one() -> None:
    """Open-Meteo stamps the block it reports; that is the event time."""
    body = {
        "current": {"time": "2026-08-25T14:45", "temperature_2m": 23.2},
        "current_units": {},
    }
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))) as client:
        readings = capture.fetch_weather(client)

    stamp = readings[0]["provider_event_time"]
    assert stamp == datetime(2026, 8, 25, 14, 45, tzinfo=timezone.utc)
    assert stamp.tzinfo is not None


def test_a_response_digest_is_recorded_but_the_payload_is_not() -> None:
    """Enough to prove the acquisition happened; not enough to redistribute.

    The licence review found retention and redistribution concerns with keeping
    raw third-party responses, so a digest stands in for the body.
    """
    body = {"current": {"time": "2026-08-25T14:45", "temperature_2m": 23.2}, "current_units": {}}
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))) as client:
        readings = capture.fetch_weather(client)

    reading = readings[0]
    assert len(reading["response_sha256"]) == 64
    assert all(c in "0123456789abcdef" for c in reading["response_sha256"])
    # The raw payload is nowhere in what gets persisted.
    assert "raw" not in reading and "payload" not in reading and "body" not in reading


def test_corridors_and_reference_points_are_inside_the_pilot_area() -> None:
    """A corridor outside Bengaluru would acquire real traffic for the wrong city."""
    for name, lat, lon in capture.PILOT_CORRIDORS + capture.WEATHER_REFERENCE_POINTS:
        assert 12.70 <= lat <= 13.20, f"{name} lat {lat} is not Bengaluru"
        assert 77.30 <= lon <= 77.90, f"{name} lon {lon} is not Bengaluru"


def test_weather_is_sampled_not_fanned_out_across_every_cell() -> None:
    """94 requests would return the same regional model output and would be
    provider abuse for no additional information."""
    assert 1 <= len(capture.WEATHER_REFERENCE_POINTS) <= 5
    assert 1 <= len(capture.PILOT_CORRIDORS) <= 12


def test_congestion_ratio_is_free_flow_over_current_not_the_inverse() -> None:
    """Above 1.0 must mean slower than free flow, or every reading inverts."""
    body = {
        "flowSegmentData": {
            "currentSpeed": 20,
            "freeFlowSpeed": 40,
            "currentTravelTime": 100,
            "freeFlowTravelTime": 50,
            "confidence": 1,
            "frc": "FRC2",
        }
    }
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))) as client:
        readings = capture.fetch_traffic(client, key="stub-not-a-real-key")

    assert readings[0]["congestion_ratio"] == pytest.approx(2.0)


def test_a_stopped_road_does_not_divide_by_zero() -> None:
    """currentSpeed of 0 is a real reading on a blocked road."""
    body = {
        "flowSegmentData": {
            "currentSpeed": 0,
            "freeFlowSpeed": 40,
            "currentTravelTime": 9999,
            "freeFlowTravelTime": 50,
            "confidence": 1,
            "frc": "FRC2",
        }
    }
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))) as client:
        readings = capture.fetch_traffic(client, key="stub-not-a-real-key")

    # Unknown, not infinite and not zero.
    assert readings[0]["congestion_ratio"] is None
    assert readings[0]["current_speed_kmph"] == 0.0


# --- the credential ----------------------------------------------------------


def test_no_credential_is_a_recordable_state_not_a_crash(monkeypatch) -> None:
    """The historical collector read TOMTOM_API_KEY, which this deployment does
    not set -- which is why it had never once acquired. Both names resolve now,
    and their absence is a state the cycle can record."""
    monkeypatch.delenv("TOMTOM_API_KEY", raising=False)
    monkeypatch.delenv("TOMTOM", raising=False)
    monkeypatch.setenv("ONEMOVE_ENV_FILE", "does-not-exist.env")
    assert capture._tomtom_key() is None
    assert "NO_CREDENTIAL" in capture._REASON_CODES

    monkeypatch.setenv("TOMTOM", "stub-value")
    assert capture._tomtom_key() == "stub-value"

    monkeypatch.setenv("TOMTOM_API_KEY", "stub-preferred")
    assert capture._tomtom_key() == "stub-preferred", "the canonical name must win"


# --- freshness integration ---------------------------------------------------


def test_an_absent_observation_is_unavailable_not_free_flowing() -> None:
    """The end-to-end statement of the rule: no data is not good news."""
    from services.zonepilot.dataquality.freshness import FreshnessState, assess

    now = datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)
    assert assess("TOMTOM", None, now=now).state is FreshnessState.UNAVAILABLE
    assert assess("TOMTOM", now - timedelta(hours=4), now=now).state is FreshnessState.STALE


def test_the_pilot_workspace_is_resolved_by_slug_not_guessed() -> None:
    """A hardcoded uuid absent from `workspaces` fails the foreign key at insert
    time; that is how the first version of this module was caught."""
    assert capture.PILOT_WORKSPACE_SLUG == "bengaluru-pilot"
    assert not hasattr(capture, "PILOT_WORKSPACE"), "the hardcoded uuid must stay gone"

    class _MissingSlug:
        def execute(self, sql, params=None):
            class _R:
                @staticmethod
                def fetchone():
                    return None

                @staticmethod
                def fetchall():
                    return [("some-other-workspace",)]

            return _R()

    with pytest.raises(LookupError, match="no workspace with slug"):
        capture.resolve_workspace(_MissingSlug(), slug="not-a-real-workspace")


def test_capture_outcome_reports_duplicates_separately_from_writes() -> None:
    """Idempotency has to be visible, or a cycle that wrote nothing looks broken."""
    outcome = capture.CaptureOutcome(capture_run_id=uuid.uuid4(), started_at=datetime.now(timezone.utc))
    assert outcome.observations_written == 0
    assert outcome.observations_skipped_as_duplicate == 0
    assert outcome.outages == []
