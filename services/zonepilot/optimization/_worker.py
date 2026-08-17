"""Private JSON worker for process-isolated CP-SAT execution."""

from __future__ import annotations

import sys

from pydantic import ValidationError

from services.zonepilot.optimization._cp_sat import optimize_facilities
from services.zonepilot.optimization.contracts import OptimizationProblem


def main() -> int:
    try:
        problem = OptimizationProblem.model_validate_json(sys.stdin.read())
    except ValidationError:
        return 2
    result = optimize_facilities(problem)
    sys.stdout.write(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
