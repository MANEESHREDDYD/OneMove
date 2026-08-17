"""R0 execution plane: repeatable, evidence-bearing provider acquisition.

The public repository owns the *source* of acquisition. The private execution
repository supplies credentials and triggers it. Nothing in this package reads a
credential from anywhere except the process environment, and nothing here writes
a credential to disk or to a log line.
"""

from services.collectors.execution.evidence import (
    artifact_hash,
    canonical_json,
    request_fingerprint,
)
from services.collectors.execution.pilot_area import PILOT_BBOX, pilot_cells
from services.collectors.execution.run_state import RunStatus

__all__ = [
    "PILOT_BBOX",
    "RunStatus",
    "artifact_hash",
    "canonical_json",
    "pilot_cells",
    "request_fingerprint",
]
