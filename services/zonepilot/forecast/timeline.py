"""Shared timestamp coercion for point-in-time forecast reads and evaluations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def coerce_utc(value: Any) -> datetime | None:
    """Coerce a timestamp to an aware UTC datetime, or None if it is not one.

    Naive timestamps are read as UTC so a mixed-awareness dataset cannot raise
    mid-comparison; anything unparseable returns None so the caller can exclude
    the record instead of guessing where it belongs on the timeline.
    """
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
