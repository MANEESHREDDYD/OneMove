"""Freshness must be computed, not asserted.

A UI that prints LIVE because a fetch once returned 200 is making a claim about
the present from evidence about the past. These tests pin the four states apart
-- in particular UNAVAILABLE, which must never collapse into a zero value or a
zero age.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from services.zonepilot.dataquality.freshness import (
    OPEN_METEO_WEATHER,
    TOMTOM_TRAFFIC,
    FreshnessPolicy,
    FreshnessState,
    assess,
    policy_for,
)

NOW = datetime(2026, 8, 25, 15, 0, tzinfo=timezone.utc)


def _at(minutes: float):
    return assess("TOMTOM", NOW - timedelta(minutes=minutes), now=NOW)


# --- the four states are genuinely different ---------------------------------


def test_absent_observation_is_unavailable_with_a_null_age() -> None:
    """UNAVAILABLE is absence, not extreme age.

    A zero age would read as an observation taken this instant. The distinction
    is the whole reason this state exists.
    """
    verdict = assess("TOMTOM", None, now=NOW)
    assert verdict.state is FreshnessState.UNAVAILABLE
    assert verdict.age is None
    assert verdict.age_seconds is None
    assert verdict.observed_at is None
    assert verdict.is_usable_as_current is False


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (0, FreshnessState.FRESH),
        (4.9, FreshnessState.FRESH),
        (5, FreshnessState.FRESH),
        (5.1, FreshnessState.DEGRADED),
        (29.9, FreshnessState.DEGRADED),
        (30, FreshnessState.DEGRADED),
        (30.1, FreshnessState.STALE),
        (600, FreshnessState.STALE),
    ],
)
def test_the_boundaries_land_where_the_policy_says(minutes: float, expected: FreshnessState) -> None:
    """Inclusive at the threshold, so the declared number is the actual number."""
    assert _at(minutes).state is expected


def test_only_fresh_and_degraded_describe_the_present() -> None:
    assert _at(1).is_usable_as_current is True
    assert _at(20).is_usable_as_current is True
    assert _at(120).is_usable_as_current is False
    assert assess("TOMTOM", None, now=NOW).is_usable_as_current is False


def test_the_age_is_published_alongside_the_state() -> None:
    """A label without an age asks the reader to trust it."""
    verdict = _at(7)
    assert verdict.age_seconds == 420
    assert verdict.observed_at == NOW - timedelta(minutes=7)


# --- per-provider cadences ---------------------------------------------------


def test_providers_do_not_share_a_cadence() -> None:
    """One threshold for both would either cry stale on weather or vouch for
    traffic that has already moved on."""
    forty_minutes_ago = NOW - timedelta(minutes=40)

    # The same instant: already history for traffic, still the current hour for
    # a weather model.
    assert assess("TOMTOM", forty_minutes_ago, now=NOW).state is FreshnessState.STALE
    assert assess("OPEN_METEO", forty_minutes_ago, now=NOW).state is FreshnessState.FRESH

    two_hours_ago = NOW - timedelta(hours=2)
    assert assess("OPEN_METEO", two_hours_ago, now=NOW).state is FreshnessState.DEGRADED


def test_an_undeclared_provider_is_rejected_not_defaulted() -> None:
    """Inheriting someone else's cadence would make FRESH unfounded."""
    with pytest.raises(KeyError) as excinfo:
        policy_for("MAPPLS")
    assert "no freshness policy declared" in str(excinfo.value)


def test_every_declared_policy_carries_its_rationale() -> None:
    """A threshold nobody can justify is a magic number."""
    for policy in (TOMTOM_TRAFFIC, OPEN_METEO_WEATHER):
        assert policy.rationale.strip(), f"{policy.provider} has no rationale"
        assert len(policy.rationale) > 80, f"{policy.provider} rationale is too thin to justify anything"


def test_a_policy_with_an_unreachable_degraded_band_is_refused() -> None:
    """If fresh_within >= degraded_within, DEGRADED can never be returned."""
    with pytest.raises(ValueError, match="DEGRADED is unreachable"):
        FreshnessPolicy(
            provider="BROKEN",
            fresh_within=timedelta(minutes=30),
            degraded_within=timedelta(minutes=5),
            rationale="x",
        )


# --- time handling -----------------------------------------------------------


def test_a_naive_timestamp_is_refused_rather_than_assumed_utc() -> None:
    """A naive timestamp compared against UTC shifts the age by the local offset.

    Silently assuming UTC would make an IST-stamped observation appear five and
    a half hours old, or five and a half hours in the future.
    """
    with pytest.raises(ValueError, match="timezone-aware"):
        assess("TOMTOM", datetime(2026, 8, 25, 14, 55), now=NOW)


def test_a_non_utc_timestamp_is_compared_correctly() -> None:
    """The same instant expressed in IST must grade identically."""
    ist = timezone(timedelta(hours=5, minutes=30))
    same_instant = (NOW - timedelta(minutes=3)).astimezone(ist)
    assert assess("TOMTOM", same_instant, now=NOW).age_seconds == 180


def test_clock_skew_cannot_manufacture_confidence() -> None:
    """A future timestamp is clamped to zero age, not treated as extra fresh."""
    verdict = assess("TOMTOM", NOW + timedelta(minutes=10), now=NOW)
    assert verdict.age == timedelta(0)
    assert verdict.state is FreshnessState.FRESH
    assert verdict.age_seconds == 0
