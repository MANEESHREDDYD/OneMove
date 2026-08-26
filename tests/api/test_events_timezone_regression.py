"""F-026: naive observed_at_device must not raise AttributeError -> 500.

services/api/routers/events.py imports `timezone` directly from datetime, but
normalised a naive timestamp with `datetime.timezone.utc`. `datetime` is bound to
the class there, which has no `timezone` attribute, so this raised AttributeError.
The surrounding handler catches only (TypeError, ValueError), so the error escaped
as an unhandled 500 on a routine ingest path.
"""

from __future__ import annotations

import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest

import services.api.routers.events as events_module


def test_naive_timestamp_normalisation_does_not_raise() -> None:
    """The exact operation that used to fail."""
    naive = datetime(2026, 8, 20, 10, 0, 0)
    assert naive.tzinfo is None
    aware = naive.replace(tzinfo=timezone.utc)
    assert aware.tzinfo is timezone.utc

    # And the misuse genuinely raises, so this test is not vacuous.
    with pytest.raises(AttributeError):
        naive.replace(tzinfo=datetime.timezone.utc)  # type: ignore[attr-defined]


def test_events_router_never_uses_datetime_timezone_attribute() -> None:
    """Guard the whole module, not just the one line that was fixed."""
    source = inspect.getsource(events_module)
    assert "datetime.timezone" not in source, (
        "events.py imports `timezone` directly; `datetime.timezone` is an AttributeError there"
    )


def test_no_module_shadowing_of_datetime_in_events() -> None:
    """`from datetime import datetime` and `import datetime` must not be mixed."""
    tree = ast.parse(Path(events_module.__file__).read_text(encoding="utf-8"))
    imports_class = any(
        isinstance(n, ast.ImportFrom) and n.module == "datetime" and any(a.name == "datetime" for a in n.names)
        for n in ast.walk(tree)
    )
    imports_module = any(
        isinstance(n, ast.Import) and any(a.name == "datetime" for a in n.names) for n in ast.walk(tree)
    )
    assert not (imports_class and imports_module), "datetime is imported both as module and class"
    assert imports_class, "events.py is expected to import the datetime class directly"
