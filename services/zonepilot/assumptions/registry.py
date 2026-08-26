"""The versioned assumption registry.

Resolution has three modes and they are deliberately not interchangeable:

``resolve_pinned``
    Exact lookup by ``assumption_set_id`` + ``version``, with the caller's
    ``sha256`` verified against the stored set. It never falls back to another
    version and never returns "the closest thing we still have". This is the mode
    point-in-time replay uses, because a replay that quietly adopts the current
    assumptions has not replayed anything -- it has made a new decision and
    labelled it with an old decision's id.

``resolve_as_of``
    The set that was in force at a given instant. Used when a historical artefact
    names no reference at all; a set that became effective after that instant is
    not eligible, no matter how current it is.

``resolve_active``
    The set to use for a *new* decision. This is the only mode that looks at
    "now", and no replay path may call it.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Iterable

from services.zonepilot.assumptions.application import AssumptionSetView
from services.zonepilot.assumptions.contracts import (
    AssumptionSet,
    AssumptionSetRef,
    AssumptionStatus,
    compute_assumption_digest,
)
from services.zonepilot.assumptions.seed import SEED_ASSUMPTION_SETS


class AssumptionRegistryError(Exception):
    """Base class for every failure to resolve an assumption set."""


class AssumptionSetNotFound(AssumptionRegistryError):
    """No registered set answers to the requested identity."""


class AssumptionSetIntegrityError(AssumptionRegistryError):
    """A set was found, but it is not the set the caller asked for."""


class AssumptionReferenceError(AssumptionRegistryError):
    """A lineage string does not identify an assumption set at all."""


class AssumptionRegistry:
    """An append-only collection of sealed assumption sets."""

    def __init__(self, sets: Iterable[AssumptionSet] = ()) -> None:
        self._lock = threading.RLock()
        self._by_version: dict[tuple[str, str], AssumptionSet] = {}
        self._by_legacy_token: dict[str, AssumptionSet] = {}
        for assumption_set in sets:
            self.register(assumption_set)

    # -- population ----------------------------------------------------------

    def register(self, assumption_set: AssumptionSet) -> AssumptionSet:
        """Add a set. Re-registering identical content is a no-op; rewriting is not.

        A published (id, version) is immutable. Silently accepting new content
        under an existing version would make every reference to that version
        ambiguous, and every replay pinned to it wrong.
        """
        key = (assumption_set.assumption_set_id, assumption_set.version)
        with self._lock:
            existing = self._by_version.get(key)
            if existing is not None and existing.sha256 != assumption_set.sha256:
                raise AssumptionSetIntegrityError(
                    f"{key[0]}@{key[1]} is already registered with digest {existing.sha256[:16]}...; "
                    f"an assumption version is immutable, publish a new version instead"
                )
            for legacy in assumption_set.legacy_tokens:
                owner = self._by_legacy_token.get(legacy)
                if owner is not None and owner.sha256 != assumption_set.sha256:
                    raise AssumptionSetIntegrityError(
                        f"legacy token {legacy!r} already resolves to "
                        f"{owner.assumption_set_id}@{owner.version}; it cannot identify two different sets"
                    )
            self._by_version[key] = assumption_set
            for legacy in assumption_set.legacy_tokens:
                self._by_legacy_token[legacy] = assumption_set
        return assumption_set

    def sets(self) -> tuple[AssumptionSet, ...]:
        with self._lock:
            return tuple(sorted(self._by_version.values(), key=lambda s: (s.effective_at, s.assumption_set_id, s.version)))

    # -- pinned resolution ---------------------------------------------------

    def resolve_pinned(self, ref: AssumptionSetRef) -> AssumptionSet:
        """Load exactly the set named by id + version + sha256, or fail closed."""
        with self._lock:
            found = self._by_version.get((ref.assumption_set_id, ref.version))
        if found is None:
            known = ", ".join(sorted(f"{i}@{v}" for i, v in self._by_version)) or "none"
            raise AssumptionSetNotFound(
                f"assumption set {ref.assumption_set_id}@{ref.version} is not registered "
                f"(registered: {known}); refusing to substitute a different version"
            )
        if found.sha256 != ref.sha256:
            raise AssumptionSetIntegrityError(
                f"assumption set {ref.assumption_set_id}@{ref.version} is registered with digest "
                f"{found.sha256[:16]}... but was referenced as {ref.sha256[:16]}...; "
                f"the stored set is not the one this artefact was built from"
            )
        recomputed = compute_assumption_digest(
            found.records,
            assumption_set_id=found.assumption_set_id,
            version=found.version,
        )
        if recomputed != ref.sha256:
            raise AssumptionSetIntegrityError(
                f"assumption set {ref.assumption_set_id}@{ref.version} no longer digests to its own seal"
            )
        return found

    def resolve_token(self, token: str) -> AssumptionSet:
        """Resolve a lineage string to the set that produced it.

        Accepts a pinned reference, or a legacy version string written before this
        registry existed and explicitly claimed by exactly one historical set.
        Anything else fails: guessing which assumptions an unlabelled artefact used
        is how "today's numbers" leak into a replay.
        """
        cleaned = (token or "").strip()
        if not cleaned:
            raise AssumptionReferenceError("no assumption reference is present on this artefact")
        if AssumptionSetRef.is_token(cleaned):
            return self.resolve_pinned(AssumptionSetRef.parse(cleaned))
        with self._lock:
            legacy = self._by_legacy_token.get(cleaned)
        if legacy is not None:
            return legacy
        raise AssumptionReferenceError(
            f"{cleaned!r} is neither a pinned assumption reference nor a known legacy assumption version; "
            f"the assumptions behind this artefact cannot be recovered"
        )

    def resolve_view_for_token(self, token: str) -> AssumptionSetView:
        return AssumptionSetView(self.resolve_token(token))

    # -- point-in-time resolution -------------------------------------------

    def resolve_as_of(self, when: datetime, *, assumption_set_id: str | None = None) -> AssumptionSet:
        """The set that was in force at ``when``.

        Drafts are excluded because they were never in force. Superseded and
        retired sets are included, because "what was true then" is exactly the
        question and the answer does not change when a successor is published.
        """
        if when.tzinfo is None:
            raise AssumptionReferenceError("point-in-time assumption resolution requires a timezone-aware instant")
        eligible = [
            candidate
            for candidate in self.sets()
            if candidate.status is not AssumptionStatus.DRAFT
            and candidate.effective_at <= when
            and (assumption_set_id is None or candidate.assumption_set_id == assumption_set_id)
        ]
        if not eligible:
            scope = assumption_set_id or "any assumption set"
            raise AssumptionSetNotFound(
                f"no version of {scope} was in force at {when.isoformat()}; "
                f"refusing to apply a later set to an earlier decision"
            )
        return max(eligible, key=lambda candidate: (candidate.effective_at, candidate.version))

    def view_as_of(self, when: datetime, *, assumption_set_id: str | None = None) -> AssumptionSetView:
        return AssumptionSetView(self.resolve_as_of(when, assumption_set_id=assumption_set_id))

    # -- current resolution (new decisions only) -----------------------------

    def resolve_active(self, *, assumption_set_id: str | None = None, now: datetime | None = None) -> AssumptionSet:
        """The set a *new* decision should be made under. Never valid for replay."""
        instant = now or datetime.now(timezone.utc)
        eligible = [
            candidate
            for candidate in self.sets()
            if candidate.status is AssumptionStatus.ACTIVE
            and candidate.effective_at <= instant
            and (assumption_set_id is None or candidate.assumption_set_id == assumption_set_id)
        ]
        if not eligible:
            scope = assumption_set_id or "any assumption set"
            raise AssumptionSetNotFound(f"no ACTIVE version of {scope} is effective at {instant.isoformat()}")
        return max(eligible, key=lambda candidate: (candidate.effective_at, candidate.version))

    def active_view(self, *, assumption_set_id: str | None = None, now: datetime | None = None) -> AssumptionSetView:
        return AssumptionSetView(self.resolve_active(assumption_set_id=assumption_set_id, now=now))


_DEFAULT_REGISTRY: AssumptionRegistry | None = None
_DEFAULT_LOCK = threading.Lock()


def default_assumption_registry() -> AssumptionRegistry:
    """The process-wide registry, seeded with every published set."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        with _DEFAULT_LOCK:
            if _DEFAULT_REGISTRY is None:
                _DEFAULT_REGISTRY = AssumptionRegistry(SEED_ASSUMPTION_SETS)
    return _DEFAULT_REGISTRY
