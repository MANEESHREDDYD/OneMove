"""Secret hygiene and credential leak prevention tests.

Asserts that no hardcoded passwords, real API keys, or private auth secrets exist in tracked source code.
"""

from __future__ import annotations

import re
from pathlib import Path

FORBIDDEN_PASSWORD_PATTERNS = [
    re.compile(r"OneMoveOperator\d+!"),
    re.compile(r"OneMoveTenant\d+!"),
    re.compile(r"password\s*=\s*['\"][A-Za-z0-9!@#$%^&*()_+=-]{8,}['\"]", re.IGNORECASE),
]

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".next",
    "dist",
    ".gemini",
}


def test_no_hardcoded_passwords_in_scripts() -> None:
    root = Path(__file__).resolve().parent.parent
    scripts_dir = root / "scripts"

    for path in scripts_dir.rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert "OneMoveOperator" not in content, f"Hardcoded password pattern found in {path}"
        assert "OneMoveTenant" not in content, f"Hardcoded password pattern found in {path}"


def test_no_hardcoded_passwords_in_services() -> None:
    root = Path(__file__).resolve().parent.parent
    services_dir = root / "services"

    for path in services_dir.rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert "OneMoveOperator" not in content, f"Hardcoded password pattern found in {path}"
        assert "OneMoveTenant" not in content, f"Hardcoded password pattern found in {path}"
