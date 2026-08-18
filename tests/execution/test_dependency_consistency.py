"""One authoritative Python dependency set.

Every Python gate installs the root and API manifests together:

    pip install -r requirements.txt -r services/api/requirements.txt

so a package pinned to two different exact versions across those files makes
the combined install unsatisfiable. That is not hypothetical: Dependabot #8
failed with ``Cannot install fastapi==0.111.0 and fastapi==0.141.1`` and #10
failed with ``Cannot install zonepilot and zonepilot[dev]==0.1.0``, because
seven packages carried duplicate pins and pyproject's dev extra disagreed with
requirements.txt.

These tests make the invariant enforceable so the failure class cannot return.
"""

from __future__ import annotations

import re
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[2]
BASE_REQUIREMENTS = ROOT / "requirements.txt"
API_REQUIREMENTS = ROOT / "services" / "api" / "requirements.txt"
PYPROJECT = ROOT / "pyproject.toml"

PIN = re.compile(r"^\s*([A-Za-z0-9._-]+)\s*==\s*([A-Za-z0-9._+!-]+)\s*$")
REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9._-]+)")


def _canonical(name: str) -> str:
    """PEP 503 normalisation: PyJWT, pyjwt and py_jwt are one project."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _direct_pins(path: Path) -> dict[str, str]:
    """Exact pins declared in this file, not following -r includes."""
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        match = PIN.match(stripped)
        if match:
            pins[_canonical(match.group(1))] = match.group(2)
    return pins


def _includes(path: Path) -> list[str]:
    return [
        line.strip().removeprefix("-r").strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("-r")
    ]


def _pyproject_dev_pins() -> dict[str, str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dev = data["project"]["optional-dependencies"]["dev"]
    pins: dict[str, str] = {}
    for entry in dev:
        match = PIN.match(entry)
        if match:
            pins[_canonical(match.group(1))] = match.group(2)
    return pins


def _pyproject_runtime_names() -> set[str]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    names = set()
    for entry in data["project"]["dependencies"]:
        match = REQUIREMENT_NAME.match(entry)
        if match:
            names.add(_canonical(match.group(1)))
    return names


def test_api_manifest_includes_the_base_manifest_instead_of_duplicating_it():
    includes = _includes(API_REQUIREMENTS)
    assert includes, (
        "services/api/requirements.txt must include the root manifest with "
        "'-r ../../requirements.txt' so shared runtime pins have one owner."
    )
    resolved = [(API_REQUIREMENTS.parent / inc).resolve() for inc in includes]
    assert BASE_REQUIREMENTS.resolve() in resolved


def test_no_package_is_pinned_to_two_different_versions():
    base = _direct_pins(BASE_REQUIREMENTS)
    api = _direct_pins(API_REQUIREMENTS)
    dev = _pyproject_dev_pins()

    conflicts = []
    for name in set(base) & set(api):
        if base[name] != api[name]:
            conflicts.append(f"{name}: requirements.txt=={base[name]} vs services/api=={api[name]}")
    for name in set(base) & set(dev):
        if base[name] != dev[name]:
            conflicts.append(f"{name}: requirements.txt=={base[name]} vs pyproject[dev]=={dev[name]}")
    for name in set(api) & set(dev):
        if api[name] != dev[name]:
            conflicts.append(f"{name}: services/api=={api[name]} vs pyproject[dev]=={dev[name]}")

    assert not conflicts, (
        "Conflicting exact pins make 'pip install -r requirements.txt "
        "-r services/api/requirements.txt' unsatisfiable:\n  " + "\n  ".join(sorted(conflicts))
    )


def test_api_manifest_does_not_redeclare_base_pins():
    base = _direct_pins(BASE_REQUIREMENTS)
    api = _direct_pins(API_REQUIREMENTS)
    duplicated = sorted(set(base) & set(api))
    assert not duplicated, (
        "These packages are pinned in both manifests, so a Dependabot bump to "
        "one side breaks the combined install: " + ", ".join(duplicated)
    )


def test_dev_tooling_is_declared_once_and_agrees_everywhere():
    base = _direct_pins(BASE_REQUIREMENTS)
    dev = _pyproject_dev_pins()
    for tool in ("pytest", "pytest-asyncio", "pytest-cov"):
        if tool in base and tool in dev:
            assert base[tool] == dev[tool], (
                f"{tool} disagrees between requirements.txt ({base[tool]}) and "
                f"pyproject dev extra ({dev[tool]}). The R1 evidence workflow "
                f"installs '.[dev]' while other gates install requirements.txt."
            )


def test_runtime_pins_are_declared_in_the_package_metadata():
    """A runtime dependency pinned for CI should also be a declared dependency."""
    declared = _pyproject_runtime_names()
    base = _direct_pins(BASE_REQUIREMENTS)
    api = _direct_pins(API_REQUIREMENTS)
    test_only = {"pytest", "pytest-asyncio", "pytest-cov", "ruff"}

    undeclared = sorted(name for name in (set(base) | set(api)) - declared - test_only)
    assert not undeclared, (
        "Pinned for CI but absent from pyproject [project.dependencies], so an "
        "editable install would not provide them: " + ", ".join(undeclared)
    )
