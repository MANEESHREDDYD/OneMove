"""How old an observation is allowed to be before we stop calling it current.

A successful API call is not freshness. A UI that prints LIVE because a fetch
once returned 200 is making a claim about the present using evidence about the
past, and the gap between the two is exactly where an operator gets misled.

So freshness is computed from the observation's own age against a declared
threshold, and the age is published beside the label. Four states, and they are
genuinely different things:

  FRESH        within the provider's expected cadence
  DEGRADED     older than expected but still decision-relevant
  STALE        too old to describe the present; usable only as history
  UNAVAILABLE  there is no observation at all

UNAVAILABLE is not a fifth grade of staleness. It is the absence of data, and it
must never be rendered as 0 mm of rain, 0 km/h of wind, or free-flowing traffic.
This module keeps it a distinct return value so a caller cannot accidentally
arithmetic its way past it.

THRESHOLDS ARE PER PROVIDER, because their cadences genuinely differ. Traffic
flow changes minute to minute; a weather model publishes on a fixed cycle and an
hour-old reading is still an honest description of the hour. Using one threshold
for both would either cry stale on weather or vouch for traffic that has moved
on. The values below are the providers' own documented cadences where they state
one, and a conservative reading where they do not -- each is annotated with which
it is, because a threshold nobody can justify is a magic number.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class FreshnessState(str, Enum):
    """The four states. UNAVAILABLE is absence, not extreme age."""

    FRESH = "FRESH"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class FreshnessPolicy:
    """Per-provider thresholds, with the reason each was chosen."""

    provider: str
    fresh_within: timedelta
    degraded_within: timedelta
    rationale: str

    def __post_init__(self) -> None:
        if self.fresh_within >= self.degraded_within:
            raise ValueError(
                f"{self.provider}: fresh_within ({self.fresh_within}) must be shorter than "
                f"degraded_within ({self.degraded_within}), otherwise DEGRADED is unreachable"
            )
        if self.fresh_within <= timedelta(0):
            raise ValueError(f"{self.provider}: fresh_within must be positive")


TOMTOM_TRAFFIC = FreshnessPolicy(
    provider="TOMTOM",
    fresh_within=timedelta(minutes=5),
    degraded_within=timedelta(minutes=30),
    rationale=(
        "TomTom refreshes flow data on the order of a minute and its own tiles carry a short "
        "cache lifetime. Five minutes is a conservative reading of that cadence rather than a "
        "documented SLA. Beyond thirty minutes a congestion reading no longer describes the "
        "current road, so it is history."
    ),
)

OPEN_METEO_WEATHER = FreshnessPolicy(
    provider="OPEN_METEO",
    fresh_within=timedelta(minutes=60),
    degraded_within=timedelta(hours=3),
    rationale=(
        "Open-Meteo serves model output on an hourly step, so a reading inside the hour is the "
        "current published state rather than a stale one. Three hours spans the typical model "
        "refresh; beyond it the run that produced the value has been superseded."
    ),
)

_POLICIES: dict[str, FreshnessPolicy] = {
    policy.provider: policy for policy in (TOMTOM_TRAFFIC, OPEN_METEO_WEATHER)
}


def policy_for(provider: str) -> FreshnessPolicy:
    """The declared policy, or a loud failure.

    Falling back to a default for an unknown provider would silently apply a
    cadence nobody chose, and the resulting FRESH label would be unfounded.
    """
    try:
        return _POLICIES[provider.upper()]
    except KeyError:
        raise KeyError(
            f"no freshness policy declared for provider {provider!r}; "
            f"declared providers are {sorted(_POLICIES)}. Add one with its rationale "
            "rather than letting an undeclared provider inherit someone else's cadence."
        ) from None


@dataclass(frozen=True)
class FreshnessVerdict:
    """The state, and the age that produced it. Both are published."""

    state: FreshnessState
    provider: str
    observed_at: datetime | None
    age: timedelta | None

    @property
    def age_seconds(self) -> int | None:
        return None if self.age is None else int(self.age.total_seconds())

    @property
    def is_usable_as_current(self) -> bool:
        """Only FRESH and DEGRADED describe the present."""
        return self.state in (FreshnessState.FRESH, FreshnessState.DEGRADED)


def assess(provider: str, observed_at: datetime | None, *, now: datetime | None = None) -> FreshnessVerdict:
    """Grade one observation's age against its provider's declared policy.

    ``observed_at`` of None means no observation exists, which is UNAVAILABLE
    with a null age -- never a zero age, and never a zero value.
    """
    declared = policy_for(provider)

    if observed_at is None:
        return FreshnessVerdict(FreshnessState.UNAVAILABLE, declared.provider, None, None)

    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError(
            f"{declared.provider}: observed_at must be timezone-aware; a naive timestamp "
            "compared against UTC silently shifts the age by the local offset"
        )

    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    age = reference - observed_at.astimezone(timezone.utc)

    # A future timestamp means clock skew between the provider, the collector and
    # this process. Treating it as very fresh would let skew manufacture
    # confidence, so it is clamped to zero age and still graded FRESH -- the
    # honest reading is "we cannot tell it is old", not "it is especially new".
    if age < timedelta(0):
        age = timedelta(0)

    if age <= declared.fresh_within:
        state = FreshnessState.FRESH
    elif age <= declared.degraded_within:
        state = FreshnessState.DEGRADED
    else:
        state = FreshnessState.STALE

    return FreshnessVerdict(state, declared.provider, observed_at.astimezone(timezone.utc), age)
