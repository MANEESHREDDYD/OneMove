"""F-019: versioned, digest-sealed assumptions with point-in-time resolution.

Public surface:

* :mod:`~services.zonepilot.assumptions.contracts` -- ``AssumptionRecord``,
  ``AssumptionSet``, ``AssumptionSetRef`` and the digest over them.
* :mod:`~services.zonepilot.assumptions.registry` -- pinned, point-in-time and
  current resolution, which are three different questions and stay separate.
* :mod:`~services.zonepilot.assumptions.application` -- how a set becomes an
  optimization problem's numbers.
* :mod:`~services.zonepilot.assumptions.sensitivity` -- LOW/BASE/HIGH re-runs.
"""

from services.zonepilot.assumptions.application import (
    AssumptionApplicationError,
    AssumptionSetView,
    ScenarioTier,
)
from services.zonepilot.assumptions.contracts import (
    UNMEASURED_PILOT_PROXY,
    AssumptionName,
    AssumptionRecord,
    AssumptionSet,
    AssumptionSetRef,
    AssumptionStatus,
    canonical_record_order,
    compute_assumption_digest,
    seal_assumption_set,
)
from services.zonepilot.assumptions.registry import (
    AssumptionReferenceError,
    AssumptionRegistry,
    AssumptionRegistryError,
    AssumptionSetIntegrityError,
    AssumptionSetNotFound,
    default_assumption_registry,
)
from services.zonepilot.assumptions.seed import (
    R1_LEGACY_TOKEN,
    R1_PILOT_PROXY_SET_ID,
    R1_PILOT_PROXY_V1_0_0,
    SEED_ASSUMPTION_SETS,
)
from services.zonepilot.assumptions.sensitivity import (
    SensitivityBand,
    SensitivityCase,
    SensitivityOutcome,
    SensitivityReport,
    derive_band_set,
    evaluate_sensitivity,
    sensitive_assumptions,
    sweep_sensitivity,
)

__all__ = [
    "UNMEASURED_PILOT_PROXY",
    "AssumptionApplicationError",
    "AssumptionName",
    "AssumptionRecord",
    "AssumptionReferenceError",
    "AssumptionRegistry",
    "AssumptionRegistryError",
    "AssumptionSet",
    "AssumptionSetIntegrityError",
    "AssumptionSetNotFound",
    "AssumptionSetRef",
    "AssumptionSetView",
    "AssumptionStatus",
    "R1_LEGACY_TOKEN",
    "R1_PILOT_PROXY_SET_ID",
    "R1_PILOT_PROXY_V1_0_0",
    "SEED_ASSUMPTION_SETS",
    "ScenarioTier",
    "SensitivityBand",
    "SensitivityCase",
    "SensitivityOutcome",
    "SensitivityReport",
    "canonical_record_order",
    "compute_assumption_digest",
    "default_assumption_registry",
    "derive_band_set",
    "evaluate_sensitivity",
    "seal_assumption_set",
    "sensitive_assumptions",
    "sweep_sensitivity",
]
