"""Private JSON worker for process-isolated CP-SAT execution.

stdout carries exactly one :class:`OptimizationResult` document and nothing
else, so the parent can keep validating it as the sole decision channel.
Measured execution cost is written to stderr as a separate
:class:`SolveTelemetry` document; it is an observation about the run, never
part of the decision.
"""

from __future__ import annotations

import json
import sys
import time

from pydantic import ValidationError

from services.zonepilot.optimization._cp_sat import solve_with_counters
from services.zonepilot.optimization.contracts import DoNothingBaseline, OptimizationProblem
from services.zonepilot.optimization.telemetry import SolveTelemetry, peak_memory_bytes

LEGACY_TIE_BREAK_FLAG = "--legacy-tie-break"


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    skip_implied_solves = LEGACY_TIE_BREAK_FLAG not in arguments
    try:
        raw = json.loads(sys.stdin.read())
        if isinstance(raw, dict) and "problem" in raw:
            problem = OptimizationProblem.model_validate(raw["problem"], strict=False)
            baseline = (
                DoNothingBaseline.model_validate(raw["baseline"], strict=False)
                if raw.get("baseline") is not None
                else None
            )
        else:
            # Backwards compatibility for direct worker callers that still send
            # only an OptimizationProblem document.
            problem = OptimizationProblem.model_validate(raw, strict=False)
            baseline = None
    except (json.JSONDecodeError, ValidationError, TypeError):
        return 2
    started = time.perf_counter()
    result, counters = solve_with_counters(
        problem,
        skip_implied_solves=skip_implied_solves,
        baseline=baseline,
    )
    elapsed = time.perf_counter() - started
    peak_bytes, measurement = peak_memory_bytes()
    telemetry = SolveTelemetry(
        cp_sat_solve_count=counters.solves,
        implied_solves_skipped=counters.implied_skips,
        solver_wall_time_seconds=elapsed,
        peak_memory_bytes=peak_bytes,
        peak_memory_measurement=measurement,
    )
    sys.stdout.write(result.model_dump_json())
    sys.stderr.write(telemetry.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
