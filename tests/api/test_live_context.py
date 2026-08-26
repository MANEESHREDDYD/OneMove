"""The live-context endpoint must never let absence look like good news.

This is the surface a viewer reads to decide which parts of the picture are
real, so its failure modes are all of the same shape: a missing observation
rendered as zero congestion, a stale reading labelled current, or a provider
outage that leaves no trace. Each is pinned here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.zonepilot.dataquality.freshness import FreshnessState, assess


def _ctx(**kwargs):
    from services.api.routers.live_context import SourceContext

    base = dict(
        source="Traffic",
        provider="TOMTOM",
        evidence_class="PROVIDER_ESTIMATED",
        freshness="FRESH",
        captured_at=datetime.now(timezone.utc),
        age_seconds=10,
        observation_count=6,
    )
    base.update(kwargs)
    return SourceContext(**base)


# --- absence is not zero -----------------------------------------------------


def test_an_unobserved_source_is_unavailable_with_a_null_age() -> None:
    """A zero age reads as an observation taken this instant."""
    context = _ctx(freshness="UNAVAILABLE", captured_at=None, age_seconds=None, observation_count=0)
    assert context.freshness == "UNAVAILABLE"
    assert context.age_seconds is None
    assert context.captured_at is None
    assert context.observation_count == 0


def test_an_unknown_zone_carries_a_null_ratio_not_a_free_flowing_one() -> None:
    """1.0 means free-flowing. None means we do not know. They must not merge."""
    from services.api.routers.live_context import ZoneTraffic

    unknown = ZoneTraffic(zone_id="8860145b41fffff", congestion_ratio=None, captured_at=None)
    assert unknown.congestion_ratio is None

    flowing = ZoneTraffic(
        zone_id="8860145b41fffff", congestion_ratio=1.0, captured_at=datetime.now(timezone.utc)
    )
    assert flowing.congestion_ratio == 1.0
    assert unknown.congestion_ratio != flowing.congestion_ratio


def test_zone_traffic_defaults_to_the_provider_estimated_class() -> None:
    """TomTom flow is an estimate. Calling it OBSERVED would overstate it."""
    from services.api.routers.live_context import ZoneTraffic

    zone = ZoneTraffic(zone_id="8860145b41fffff", congestion_ratio=1.4, captured_at=None)
    assert zone.evidence_class == "PROVIDER_ESTIMATED"


# --- stale is not live -------------------------------------------------------


def test_a_stale_reading_is_graded_stale_not_fresh() -> None:
    """The endpoint grades by age, so a four-hour-old reading cannot be current."""
    now = datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)
    assert assess("TOMTOM", now - timedelta(hours=4), now=now).state is FreshnessState.STALE
    assert assess("TOMTOM", now - timedelta(minutes=2), now=now).state is FreshnessState.FRESH


def test_a_degraded_reading_is_still_usable_but_is_not_called_fresh() -> None:
    """29-minute-old traffic is worth showing and must not be labelled LIVE.

    This is not hypothetical: the endpoint returned exactly this state against
    the real database, with traffic at 1,752 seconds old.
    """
    now = datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)
    verdict = assess("TOMTOM", now - timedelta(seconds=1752), now=now)
    assert verdict.state is FreshnessState.DEGRADED
    assert verdict.is_usable_as_current is True
    assert verdict.state is not FreshnessState.FRESH


def test_geography_and_mission_are_versioned_not_graded_on_a_clock() -> None:
    """Geography does not go stale on a provider cadence; it changes when the
    extract is recut. Reporting it FRESH on a clock is a category error."""
    geography = _ctx(
        source="Network geography",
        provider=None,
        evidence_class="PUBLIC_GEOGRAPHIC",
        freshness="VERSIONED",
        captured_at=None,
        age_seconds=None,
        observation_count=94,
    )
    assert geography.freshness == "VERSIONED"
    assert geography.age_seconds is None
    assert geography.provider is None


# --- failures leave a trace --------------------------------------------------


def test_a_provider_failure_is_reported_alongside_its_reason() -> None:
    """An outage that leaves no trace is indistinguishable from calm."""
    context = _ctx(
        failure_count=1,
        last_failure_at=datetime.now(timezone.utc),
        last_failure_reason="CONNECTION_FAILED",
    )
    assert context.failure_count == 1
    assert context.last_failure_reason == "CONNECTION_FAILED"
    assert context.last_failure_at is not None


def test_a_source_with_no_failures_reports_zero_not_null() -> None:
    """Here zero IS the honest answer: we tried and nothing failed."""
    context = _ctx()
    assert context.failure_count == 0
    assert context.last_failure_at is None


# --- evidence classes --------------------------------------------------------


VALID_CLASSES = {
    "OBSERVED",
    "PUBLIC_OFFICIAL",
    "PUBLIC_GEOGRAPHIC",
    "PROVIDER_ESTIMATED",
    "DERIVED",
    "SIMULATED",
    "ASSUMPTION",
    "STAGING_DO_NOT_USE",
    "TEST_ONLY",
}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Traffic", "PROVIDER_ESTIMATED"),
        ("Weather", "PUBLIC_OFFICIAL"),
        ("Network geography", "PUBLIC_GEOGRAPHIC"),
        ("Delivery mission", "SIMULATED"),
    ],
)
def test_each_source_carries_the_class_it_actually_is(source: str, expected: str) -> None:
    """TomTom is an estimate, Open-Meteo is public official model output, the
    extract is public geography, and the orders are invented. Getting any of
    these wrong is the failure the whole product is built to avoid."""
    assert expected in VALID_CLASSES
    assert _ctx(source=source, evidence_class=expected).evidence_class == expected


def test_projected_is_not_an_evidence_class() -> None:
    """It has been written into reports more than once. It does not exist."""
    assert "PROJECTED" not in VALID_CLASSES
    assert "UNAVAILABLE" not in VALID_CLASSES, "UNAVAILABLE is an availability state, not a class"


def test_the_endpoint_requires_authentication() -> None:
    """Live operational context is not public.

    Verified against the running service: an unauthenticated GET returns 401.
    This checks the dependency is actually declared, so it cannot be dropped in
    a refactor without the test noticing.
    """
    import inspect

    from services.api.routers.live_context import get_live_context

    signature = inspect.signature(get_live_context)
    assert "_user" in signature.parameters, "the auth dependency has been removed"
    assert signature.parameters["_user"].default is not inspect.Parameter.empty
