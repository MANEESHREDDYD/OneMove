"""Database DSN resolver honoring exact PostgreSQL pooler credentials."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote


def get_database_dsn() -> str:
    # Check for direct valid pooler in environment
    env_dsn = os.environ.get("DATABASE_URL") or os.environ.get("EXECUTION_DATABASE_URL")
    if env_dsn and "@aws-0-ap-southeast-1.pooler.supabase.com" in env_dsn:
        return env_dsn

    # Canonical active hosted Supabase database pooler
    return "postgresql://postgres.puygqvnhwsjkspoprfkb:RandomUser%4012@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres?sslmode=require"
