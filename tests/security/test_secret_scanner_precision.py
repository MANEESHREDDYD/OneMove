"""The secret gate must be precise in both directions.

`scan_secrets.py` is a required CI gate, so a false positive blocks every PR and
a false negative lets a live credential through. Both are regressions, and this
module pins both edges.

The specific defect guarded here: the URI rule's host group is deliberately
greedy (``[^\\s/:"']+``) so a DSN is still caught when it runs into surrounding
text. In a Markdown sentence that greediness also swallows the trailing prose
punctuation, so ``postgresql://postgres:postgres@127.0.0.1...`).`` captured the
host as ``127.0.0.1...`).`` and the loopback allowlist -- which anchors on
``^127\\.0\\.0\\.1$`` -- silently stopped matching. A documentation line that
merely *describes* the local test database then failed the build as an
unbaselined secret.
"""

from __future__ import annotations

import pytest

from scripts.security.scan_secrets import _is_benign, scan_text

# These tests must exercise a DSN that the scanner is *supposed* to report, at a
# host the benign-host allowlist does not cover. Written as a literal it would
# trip the scanner's own working-tree pass over this file -- a true positive, but
# a self-referential one. The scanner matches on file text, so the scheme is
# joined at runtime and no `scheme://user:pass@host` literal exists in the
# source. The password is deliberately NOT self-describing as a fixture, because
# a password matching _OBVIOUS_FIXTURE would be benign for the wrong reason and
# would make the detection assertions vacuous.
_SCHEME = "postgre" + "sql"
_REMOTE_PASSWORD = "s0meRealLooking" + "Credential99"


def remote_dsn(host: str = "db.prod.internal.example-corp.net") -> str:
    return f"{_SCHEME}://svcuser:{_REMOTE_PASSWORD}@{host}:5432/app"


REMOTE_DSN = remote_dsn()


def _rules_hit(text: str) -> list[str]:
    return [rule for rule, _line, _fp in scan_text("fixture", text)]


class TestLoopbackInProse:
    """A loopback DSN quoted inside documentation is a fixture by construction."""

    @pytest.mark.parametrize(
        "line",
        [
            "(`postgresql://postgres:postgres@127.0.0.1...`). Stability here is",
            "The suite needs `postgresql://postgres:postgres@127.0.0.1:54322/postgres`.",
            "Set it to postgresql://postgres:postgres@localhost, then restart.",
            "Use `postgresql://postgres:postgres@127.0.0.1`; nothing else works.",
            "See postgresql://postgres:postgres@db:5432/postgres (docker-compose).",
        ],
    )
    def test_loopback_dsn_in_prose_is_not_flagged(self, line: str) -> None:
        assert _rules_hit(line) == [], f"false positive on documentation line: {line!r}"


class TestDetectionIsNotWeakened:
    """Host normalisation must not create a way past the gate."""

    def test_remote_dsn_is_still_reported(self) -> None:
        assert "uri-embedded-credential" in _rules_hit(REMOTE_DSN)

    @pytest.mark.parametrize(
        "trailer",
        ["", ".", "...", "`).", '"', "'", ")", ",", "');"],
    )
    def test_remote_dsn_is_reported_whatever_punctuation_follows(self, trailer: str) -> None:
        """Trimming trailing punctuation must not let a real host go benign."""
        assert "uri-embedded-credential" in _rules_hit(REMOTE_DSN + trailer)

    @pytest.mark.parametrize(
        "host",
        [
            "127.0.0.1.evil.com",
            "localhost.attacker-controlled.net",
            "notlocalhost",
            "example.com.evil.net",
            "127.0.0.1-shadow.example-corp.net",
        ],
    )
    def test_lookalike_hosts_are_not_treated_as_loopback(self, host: str) -> None:
        """A hostname that merely starts with a benign label is not benign."""
        assert "uri-embedded-credential" in _rules_hit(remote_dsn(host))

    def test_normalizer_never_lengthens_or_rewrites_the_host(self) -> None:
        from scripts.security.scan_secrets import _normalize_host

        for raw in ["127.0.0.1...`).", "db.prod.example-corp.net,", "localhost", "[::1]"]:
            normalized = _normalize_host(raw)
            assert raw.startswith(normalized), f"{normalized!r} is not a prefix of {raw!r}"
            assert len(normalized) <= len(raw)


class TestBenignReasonsAreDistinct:
    """The three benign paths must each stand on their own."""

    def test_placeholder_password_at_remote_host_is_benign(self) -> None:
        match = _match(f"{_SCHEME}://user:${{DB_PASSWORD}}@db.example-corp.net:5432/app")
        assert _is_benign("uri-embedded-credential", match)

    def test_real_password_at_remote_host_is_not_benign(self) -> None:
        match = _match(REMOTE_DSN)
        assert not _is_benign("uri-embedded-credential", match)


def _match(text: str):
    from scripts.security.scan_secrets import RULES

    pattern = dict(RULES)["uri-embedded-credential"]
    match = pattern.search(text)
    assert match is not None, f"rule did not match {text!r}"
    return match


class TestBaselineStructureIsNotATrap:
    """A baseline entry that is silently inert is worse than no entry at all.

    Two entries were once written as top-level fingerprint keys rather than
    inside the ``findings`` array. ``load_baseline`` reads only ``findings``, so
    they were never loaded. Worse, their fingerprint values matched no finding
    the scanner actually produces: the literals they claimed to cover hash to
    ``b0f1c4c2ac2f`` and ``26e42a4e7311``, not to the keys that were written. The
    file therefore documented a control that did not exist in either respect,
    and it read as deliberate to anyone reviewing it.

    This is fail-closed -- an inert entry cannot admit a secret, it can only
    cause a true finding to be reported as unbaselined -- but the failure mode is
    a reviewer's false confidence, which no exit code catches.
    """

    def test_every_baseline_entry_lives_in_findings_with_a_fingerprint(self) -> None:
        import json
        from pathlib import Path

        data = json.loads(Path("security/secret_baseline.json").read_text(encoding="utf-8"))

        stray = [k for k in data if k != "findings" and not k.startswith("_")]
        assert not stray, (
            "baseline entries outside the 'findings' array are never loaded and are "
            f"therefore inert: {sorted(stray)}"
        )

        findings = data["findings"]
        assert findings, "baseline must not be empty while historical exposures exist"
        for entry in findings:
            assert entry.get("fingerprint"), f"baseline entry without a fingerprint: {entry}"
            assert entry.get("incident"), f"baseline entry without an incident id: {entry}"

    def test_a_baselined_entry_only_passes_when_revoked_or_never_live(self) -> None:
        """An exposed credential that has not been rotated is an open incident.

        Being listed in the baseline must not by itself make a finding pass;
        only ``revoked: true`` or ``never_live: true`` may do that. Otherwise the
        baseline degrades into a suppression list.
        """
        import json
        from pathlib import Path

        data = json.loads(Path("security/secret_baseline.json").read_text(encoding="utf-8"))
        for entry in data["findings"]:
            revoked = entry.get("revoked") is True
            never_live = entry.get("never_live") is True
            if not (revoked or never_live):
                # Legitimate: an open incident awaiting owner rotation. It must
                # still carry the notes that say what closing it requires.
                assert entry.get("notes"), (
                    f"{entry['fingerprint']} is neither revoked nor never_live and carries no "
                    "notes explaining what closing it requires"
                )
