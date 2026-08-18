"""The acquisition run state machine, mirrored exactly by ``zonepilot_exec.run_status``."""

from __future__ import annotations

from enum import Enum


class RunStatus(str, Enum):
    """Every acquisition attempt ends in exactly one terminal state."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    DEGRADED = "DEGRADED"
    SKIPPED_NO_CHANGE = "SKIPPED_NO_CHANGE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    RATE_LIMITED = "RATE_LIMITED"

    @property
    def is_terminal(self) -> bool:
        return self not in _NON_TERMINAL

    @property
    def is_failure(self) -> bool:
        return self in _FAILURE_STATES


_NON_TERMINAL = frozenset({RunStatus.PENDING, RunStatus.RUNNING})

_FAILURE_STATES = frozenset(
    {
        RunStatus.FAILED,
        RunStatus.PARTIAL,
        RunStatus.DEGRADED,
        RunStatus.AUTH_REQUIRED,
        RunStatus.RATE_LIMITED,
    }
)

# The only legal moves. A terminal state has no outgoing edges: retries create a
# new run row rather than rewriting the history of an old one.
ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.PENDING: frozenset(
        {
            RunStatus.RUNNING,
            RunStatus.FAILED,
            RunStatus.SKIPPED_NO_CHANGE,
            RunStatus.AUTH_REQUIRED,
            RunStatus.RATE_LIMITED,
        }
    ),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.SUCCESS,
            RunStatus.PARTIAL,
            RunStatus.FAILED,
            RunStatus.DEGRADED,
            RunStatus.SKIPPED_NO_CHANGE,
            RunStatus.AUTH_REQUIRED,
            RunStatus.RATE_LIMITED,
        }
    ),
    RunStatus.SUCCESS: frozenset(),
    RunStatus.PARTIAL: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.DEGRADED: frozenset(),
    RunStatus.SKIPPED_NO_CHANGE: frozenset(),
    RunStatus.AUTH_REQUIRED: frozenset(),
    RunStatus.RATE_LIMITED: frozenset(),
}


class IllegalTransition(RuntimeError):
    """Raised when code tries to move a run into a state the machine forbids."""


def assert_transition(current: RunStatus, target: RunStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise IllegalTransition(f"{current.value} -> {target.value} is not a legal run transition")


def status_for_http_error(status_code: int) -> RunStatus:
    """Map a provider HTTP failure onto the run state machine."""

    if status_code in (401, 403):
        return RunStatus.AUTH_REQUIRED
    if status_code == 429:
        return RunStatus.RATE_LIMITED
    return RunStatus.FAILED
