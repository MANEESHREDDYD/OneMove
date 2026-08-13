import json
import re
from datetime import datetime
from pathlib import Path

PROGRAM_STATE_PATH = Path(__file__).parents[2] / "docs" / "execution" / "zonepilot_program_state.json"
HUMAN_STATE_PATH = PROGRAM_STATE_PATH.with_name("ZONEPILOT_PROGRAM_STATE.md")

REQUIRED_KEYS = {
    "updated_at",
    "repository",
    "branch",
    "head_sha",
    "base_sha",
    "current_milestone",
    "r0_5_status",
    "r1_status",
    "r2_status",
    "implemented_estimate",
    "verified_estimate",
    "release_ready_estimate",
    "active_workstreams",
    "completed_workstreams",
    "failed_workflows",
    "current_p0",
    "current_p1",
    "owner_blockers",
    "last_successful_test_matrix",
    "next_executable_tasks",
}


def load_state() -> dict:
    return json.loads(PROGRAM_STATE_PATH.read_text(encoding="utf-8"))


def test_program_state_contains_required_restart_contract():
    state = load_state()

    assert REQUIRED_KEYS <= state.keys()
    assert re.fullmatch(r"[0-9a-f]{40}", state["head_sha"])
    assert re.fullmatch(r"[0-9a-f]{40}", state["base_sha"])
    assert datetime.fromisoformat(state["updated_at"].replace("Z", "+00:00")).utcoffset() is not None
    assert state["repository"].startswith("https://github.com/")
    assert state["next_executable_tasks"]
    assert HUMAN_STATE_PATH.is_file()


def test_program_state_estimates_are_conservative_percentages():
    state = load_state()

    estimates = [
        state["implemented_estimate"],
        state["verified_estimate"],
        state["release_ready_estimate"],
    ]
    assert all(isinstance(estimate, int) and 0 <= estimate <= 100 for estimate in estimates)
    assert state["release_ready_estimate"] <= state["verified_estimate"] <= state["implemented_estimate"]


def test_failed_current_release_gate_cannot_coexist_with_completed_r1_claim():
    state = load_state()
    failed_current_release = any(
        workflow["head_sha"] == state["head_sha"]
        and workflow["workflow"] == "ZonePilot Release Validation"
        and workflow["conclusion"] != "success"
        for workflow in state["failed_workflows"]
    )

    if failed_current_release:
        assert "COMPLETE" not in state["r1_status"]
        assert state["release_ready_estimate"] < 100


def test_every_progress_and_blocker_entry_carries_evidence():
    state = load_state()

    for collection in ("active_workstreams", "completed_workstreams", "current_p0", "current_p1", "owner_blockers"):
        assert all(item.get("evidence") for item in state[collection])
