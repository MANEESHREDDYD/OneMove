"""ZonePilot runtime release identity and version helpers."""

from __future__ import annotations

import os

CURRENT_RELEASE_SHA = "daf7ca5c222f80a84ec1ebd1f5b5c337e41a7fc1"
CURRENT_APP_VERSION = "1.5.1"
CURRENT_SCHEMA_VERSION = "1.0.0"


def current_release_sha() -> str:
    """Return the exact verified Git commit SHA for the active deployment."""
    return (
        os.environ.get("ZONEPILOT_GIT_SHA")
        or os.environ.get("RAILWAY_GIT_COMMIT_SHA")
        or os.environ.get("GITHUB_SHA")
        or CURRENT_RELEASE_SHA
    ).strip()


def current_app_version() -> str:
    return os.environ.get("ZONEPILOT_APP_VERSION", CURRENT_APP_VERSION).strip()


def current_schema_version() -> str:
    return os.environ.get("ZONEPILOT_SCHEMA_VERSION", CURRENT_SCHEMA_VERSION).strip()
