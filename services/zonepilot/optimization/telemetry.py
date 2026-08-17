"""Measured execution characteristics for a single optimizer run.

Telemetry is deliberately separate from :class:`OptimizationResult`. A result
is a decision contract; telemetry is an observation about the machine that
produced it. Keeping them apart means a performance measurement can never be
mistaken for a business outcome, and the result contract stays byte-stable
while telemetry evolves.
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class MemoryMeasurement(str, Enum):
    """How the peak resident memory figure was obtained."""

    POSIX_MAX_RSS = "POSIX_MAX_RSS"
    WINDOWS_PEAK_WORKING_SET = "WINDOWS_PEAK_WORKING_SET"
    UNAVAILABLE = "UNAVAILABLE"


class SolveTelemetry(StrictContract):
    """Measured cost of one canonical optimizer run.

    ``cp_sat_solve_count`` counts every CP-SAT ``solve()`` invocation, including
    the primary solve and every lexicographic tie-break solve.
    ``implied_solves_skipped`` counts tie-break variables whose value was
    uniquely forced by constraints already present in the model, so no solve was
    required to determine them.
    """

    schema_name: Literal["zonepilot.optimization_solve_telemetry"] = "zonepilot.optimization_solve_telemetry"
    schema_version: Literal["1.0.0"] = "1.0.0"
    cp_sat_solve_count: int = Field(ge=0)
    implied_solves_skipped: int = Field(ge=0)
    solver_wall_time_seconds: float = Field(ge=0.0)
    peak_memory_bytes: int = Field(ge=0)
    peak_memory_measurement: MemoryMeasurement


def peak_memory_bytes() -> tuple[int, MemoryMeasurement]:
    """Return peak resident memory for this process using stdlib only.

    OR-Tools allocates most of its working set inside native code, so a Python
    allocator probe such as ``tracemalloc`` would systematically under-report.
    The operating system's own high-water mark is used instead.
    """

    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes

            class _ProcessMemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.wintypes.DWORD),
                    ("PageFaultCount", ctypes.wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            kernel32.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
            kernel32.GetCurrentProcess.argtypes = []
            psapi.GetProcessMemoryInfo.restype = ctypes.wintypes.BOOL
            psapi.GetProcessMemoryInfo.argtypes = [
                ctypes.wintypes.HANDLE,
                ctypes.POINTER(_ProcessMemoryCounters),
                ctypes.wintypes.DWORD,
            ]
            counters = _ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
            if not psapi.GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            ):
                return 0, MemoryMeasurement.UNAVAILABLE
            return int(counters.PeakWorkingSetSize), MemoryMeasurement.WINDOWS_PEAK_WORKING_SET
        except Exception:
            return 0, MemoryMeasurement.UNAVAILABLE

    try:
        import resource

        max_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        return 0, MemoryMeasurement.UNAVAILABLE
    # Linux reports kilobytes; macOS reports bytes.
    scale = 1 if sys.platform == "darwin" else 1024
    return int(max_rss) * scale, MemoryMeasurement.POSIX_MAX_RSS
