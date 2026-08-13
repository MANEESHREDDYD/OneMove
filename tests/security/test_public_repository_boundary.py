import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_TEXT_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "personal email": re.compile(rb"[A-Za-z0-9._%+-]+@(?:gmail|outlook|yahoo|hotmail)\.[A-Za-z]{2,}"),
}
KNOWN_PUBLISHED_TEST_SECRETS = {
    b"REDACTED_SYNTHETIC_TEST_SECRET",
    b"REDACTED_SYNTHETIC_TEST_SECRET",
}


def test_local_owner_credential_file_is_ignored():
    ignore_rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "OneMove.env" in ignore_rules


def test_program_state_declares_public_source_private_execution_boundary():
    state = json.loads((ROOT / "docs/execution/zonepilot_program_state.json").read_text(encoding="utf-8"))
    assert state["repository_visibility"] == "PUBLIC_SOURCE_REPOSITORY"
    assert state["private_execution_boundary"] == "SEPARATE_PRIVATE_REPOSITORY_OR_MANAGED_STORAGE"


def test_historical_supabase_report_contains_no_personal_or_hosted_identifiers():
    report = (ROOT / "docs/SUPABASE_CONNECTION_REPORT.md").read_text(encoding="utf-8")
    assert "@gmail.com" not in report.lower()
    assert ".supabase.co" not in report.lower()


def test_tracked_public_tree_contains_no_high_confidence_secret_or_personal_identifier():
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    findings: list[str] = []
    for raw_path in tracked:
        if not raw_path:
            continue
        path = ROOT / raw_path.decode("utf-8")
        if not path.is_file():
            continue
        body = path.read_bytes()
        if b"\0" in body[:8192]:
            continue
        for known_secret in KNOWN_PUBLISHED_TEST_SECRETS:
            if known_secret in body and path != Path(__file__):
                findings.append(f"published test secret: {path.relative_to(ROOT).as_posix()}")
        for label, pattern in FORBIDDEN_TEXT_PATTERNS.items():
            if pattern.search(body):
                findings.append(f"{label}: {path.relative_to(ROOT).as_posix()}")

    assert findings == []


def test_private_or_generated_artifacts_are_not_tracked():
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")
    paths = {raw_path.decode("utf-8") for raw_path in tracked if raw_path}
    forbidden_prefixes = ("data/geo/", "data_root/private/")
    forbidden_paths = {
        "log.txt",
        "reports/pre_zonepilot_audit/00_REPOSITORY_STATE.md",
        "reports/zonepilot_build/00_BUILD_START_STATE.md",
    }

    assert not any(path.startswith(forbidden_prefixes) for path in paths)
    assert not any(path.endswith(".parquet") for path in paths)
    assert paths.isdisjoint(forbidden_paths)
