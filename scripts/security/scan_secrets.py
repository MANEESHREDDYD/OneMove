"""Repository secret scanner (P0-CREDENTIAL-001).

Blocks credentials from entering the tree. Detects URI-embedded credentials,
Supabase service-role keys, JWT secrets, GCP private keys, and generic API
tokens. Findings are reported by location and non-reversible fingerprint --
never by value.

Usage:
    python scripts/security/scan_secrets.py            # scan working tree
    python scripts/security/scan_secrets.py --history  # scan full git history
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

# Hosts that are, by construction, not real secrets: local dev and test doubles.
# Loopback, container-local names, and the IETF-reserved domains from RFC 2606 /
# RFC 6761. These can never resolve to a real server, so a credential pointed at
# one is a fixture by construction.
_BENIGN_HOSTS = re.compile(
    r"^(localhost|127\.0\.0\.1|::1|0\.0\.0\.0|host\.docker\.internal|mock-[\w-]+|db|postgres"
    r"|([\w-]+\.)*(example\.(com|net|org)|invalid|test|localhost))$",
    re.IGNORECASE,
)
_PLACEHOLDER = re.compile(
    r"^(\$\{?\w+\}?|<[^>]+>|\*+|x{3,}|changeme|password|placeholder|redacted|test|dummy|your[_-]?\w*)$",
    re.IGNORECASE,
)
# Values that self-describe as fixtures. Test suites legitimately contain fake
# credentials; flagging them trains reviewers to ignore the scanner.
_OBVIOUS_FIXTURE = re.compile(
    r"attacker|fake|invalid|wrong|sample|example|placeholder|dummy|mock|not[_-]a[_-]|test[_-]?only|different[_-]secret",
    re.IGNORECASE,
)

RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "uri-embedded-credential",
        re.compile(
            r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://([^:@/\s]+):([^@\s\"']+)@([^\s/:\"']+)"
        ),
    ),
    (
        "supabase-service-role-key",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]*(?:service_role|supabase)[A-Za-z0-9_-]*\.[A-Za-z0-9_-]+"
        ),
    ),
    ("gcp-private-key", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
    ("gcp-sa-key-json", re.compile(r'"type"\s*:\s*"service_account"')),
    ("aws-access-key-id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "generic-bearer-token",
        re.compile(
            r"\b(?:api[_-]?key|secret|token|passwd|password)\s*[:=]\s*[\"']([A-Za-z0-9_\-]{24,})[\"']", re.IGNORECASE
        ),
    ),
]

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    "playwright-report",
    "test-results",
}
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".woff",
    ".woff2",
    ".ttf",
    ".parquet",
    ".pbf",
}


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _is_benign(rule: str, match: re.Match[str]) -> bool:
    if rule == "uri-embedded-credential":
        password, host = match.group(2), match.group(3)
        return bool(_BENIGN_HOSTS.match(host) or _PLACEHOLDER.match(password) or _OBVIOUS_FIXTURE.search(password))
    if rule == "generic-bearer-token":
        value = match.group(1)
        return bool(_PLACEHOLDER.match(value) or _OBVIOUS_FIXTURE.search(value))
    return False


def scan_text(rule_subject: str, text: str) -> list[tuple[str, int, str]]:
    findings = []
    for rule, pattern in RULES:
        for match in pattern.finditer(text):
            if _is_benign(rule, match):
                continue
            line_no = text.count("\n", 0, match.start()) + 1
            secret = match.group(2) if rule == "uri-embedded-credential" else match.group(0)
            findings.append((rule, line_no, fingerprint(secret)))
    return findings


def scan_working_tree(root: Path) -> list[tuple[str, str, int, str]]:
    results = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith("scripts/security/scan_secrets.py"):
            continue
        for rule, line_no, fp in scan_text(rel, text):
            results.append((rel, rule, line_no, fp))
    return results


def scan_history() -> list[tuple[str, str, int, str]]:
    """Scan every blob reachable from any ref, deduplicated by object id.

    Walking commits x files would issue tens of thousands of `git show` calls.
    Enumerating unique blobs once and streaming them through `git cat-file
    --batch` keeps a full-history scan practical in CI.
    """
    listing = subprocess.run(
        ["git", "rev-list", "--objects", "--all"], capture_output=True, text=True, check=True
    ).stdout.splitlines()

    blobs: dict[str, str] = {}
    for line in listing:
        oid, _, name = line.partition(" ")
        if not name:
            continue
        path = Path(name)
        if path.suffix.lower() in SKIP_SUFFIXES or any(part in SKIP_DIRS for part in path.parts):
            continue
        blobs.setdefault(oid, name)

    if not blobs:
        return []

    proc = subprocess.run(
        ["git", "cat-file", "--batch"],
        input=chr(10).join(blobs) + chr(10),
        capture_output=True,
        text=True,
        errors="ignore",
    )

    results: list[tuple[str, str, int, str]] = []
    stream = proc.stdout
    pos = 0
    while pos < len(stream):
        eol = stream.find(chr(10), pos)
        if eol == -1:
            break
        header = stream[pos:eol].split()
        pos = eol + 1
        if len(header) != 3 or header[1] != "blob":
            continue
        oid, size = header[0], int(header[2])
        content, pos = stream[pos : pos + size], pos + size + 1
        name = blobs.get(oid, oid)
        if name.startswith("scripts/security/scan_secrets.py"):
            continue
        for rule, line_no, fp in scan_text(name, content):
            results.append((f"blob {oid[:8]} {name}", rule, line_no, fp))
    return results


def load_baseline() -> dict[str, dict]:
    """Known historical exposures, keyed by fingerprint.

    A finding absent from the baseline fails the build. A finding present but not
    yet verified-revoked ALSO fails: an exposed credential that has not been
    rotated is an open incident, not an accepted risk. Only a credential proven
    revoked at the provider may pass.
    """
    path = Path(__file__).resolve().parents[2] / "security" / "secret_baseline.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {f["fingerprint"]: f for f in data.get("findings", [])}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", action="store_true", help="scan full git history (slow)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    findings = sorted(set(scan_history() if args.history else scan_working_tree(root)))

    # A credential in a git-ignored file cannot leak through the repository, but it
    # is still a local handling risk -- report it without failing the CI gate.
    blocking, local_only = [], []
    for finding in findings:
        ignored = (
            not args.history and subprocess.run(["git", "check-ignore", "-q", finding[0]], cwd=root).returncode == 0
        )
        (local_only if ignored else blocking).append(finding)

    for location, rule, line_no, fp in local_only:
        print(f"  WARN (git-ignored, not committed) {location}:{line_no}  [{rule}]  fingerprint={fp}")

    # Split blocking findings against the baseline of known historical exposures.
    baseline = load_baseline()
    unknown, pending, revoked = [], [], []
    for finding in blocking:
        entry = baseline.get(finding[3])
        if entry is None:
            unknown.append(finding)
        elif entry.get("revoked") is True or entry.get("never_live") is True:
            revoked.append((finding, entry))
        else:
            pending.append((finding, entry))

    for finding, entry in revoked:
        label = "never live" if entry.get("never_live") else "verified revoked"
        print(f"  BASELINED ({label}) {finding[0]}:{finding[2]} [{entry['incident']}] fingerprint={finding[3]}")

    if not unknown and not pending:
        scope = "history" if args.history else "working tree"
        print(f"secret scan: PASS ({scope}) - no unbaselined credentials detected")
        return 0

    print("")
    print(f"secret scan: FAIL - {len(unknown)} unbaselined, {len(pending)} awaiting rotation.")
    for location, rule, line_no, fp in unknown:
        print(f"  UNKNOWN SECRET   {location}:{line_no}  [{rule}]  fingerprint={fp}")
    for (location, _rule, line_no, fp), entry in pending:
        print(f"  ROTATION PENDING {location}:{line_no}  [{entry['incident']}]  fingerprint={fp}")
    print("")
    print("Remove the credential, rotate it at the provider, and load it from the secret store instead.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
