"""Does the decision survive the assumption being wrong?

An assumption with a stated range is only useful if somebody re-runs the decision
at the ends of that range. This module does exactly that and reports the one thing
that matters: whether the answer moved. If the selected facilities and the
objective are identical at LOW, BASE and HIGH, the assumption is decoration and
can be said so. If they differ, the decision is resting on a number nobody
measured, and that is a finding.

The base set is never mutated. Each band is evaluated against a *derived* set --
new records, new digest, ``DRAFT`` status, and a version that could never be
mistaken for a published one -- so a sensitivity run cannot leak into the registry
or into a decision's lineage.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Callable, Iterable, Sequence

from pydantic import Field

from services.zonepilot.assumptions.application import AssumptionSetView
from services.zonepilot.assumptions.contracts import (
    AssumptionRecord,
    AssumptionSet,
    AssumptionStatus,
    AssumptionValue,
    StrictContract,
    seal_assumption_set,
)

_SLUG = re.compile(r"[^0-9A-Za-z]+")


class SensitivityBand(str, Enum):
    LOW = "LOW"
    BASE = "BASE"
    HIGH = "HIGH"


class SensitivityOutcome(StrictContract):
    """What re-running the decision under one band produced."""

    opened_facility_ids: tuple[str, ...]
    objective_value: int


class SensitivityCase(StrictContract):
    band: SensitivityBand
    value: AssumptionValue
    assumption_version: str
    opened_facility_ids: tuple[str, ...]
    objective_value: int


class SensitivityReport(StrictContract):
    """One assumption, three evaluations, and whether the decision moved."""

    assumption_set_id: str
    version: str
    sha256: str
    assumption_name: str
    unit: str
    source: str
    base_value: AssumptionValue
    low_value: AssumptionValue
    high_value: AssumptionValue
    cases: tuple[SensitivityCase, ...] = Field(min_length=3, max_length=3)
    facility_selection_changed: bool
    objective_changed: bool

    def case(self, band: SensitivityBand) -> SensitivityCase:
        for candidate in self.cases:
            if candidate.band is band:
                return candidate
        raise KeyError(f"no {band.value} case in this report")

    @property
    def decision_is_sensitive(self) -> bool:
        """True when the assumption's stated range can change the recommendation."""
        return self.facility_selection_changed or self.objective_changed


def _variant_version(base_version: str, name: str, band: SensitivityBand) -> str:
    return f"{base_version}-sensitivity-{band.value.lower()}-{_SLUG.sub('-', name).strip('-').lower()}"


def derive_band_set(
    assumption_set: AssumptionSet,
    *,
    name: str,
    value: AssumptionValue,
    band: SensitivityBand,
) -> AssumptionSet:
    """A new sealed set identical to ``assumption_set`` except for one value.

    The receiver is not touched. The derivative is ``DRAFT``, so point-in-time
    resolution can never select it, and carries a version that names the band it
    was produced for.
    """
    target = assumption_set.record(name)
    records: list[AssumptionRecord] = [
        record.with_value(value) if record.name == target.name else record for record in assumption_set.records
    ]
    return seal_assumption_set(
        assumption_set_id=assumption_set.assumption_set_id,
        version=_variant_version(assumption_set.version, name, band),
        created_at=assumption_set.created_at,
        effective_at=assumption_set.effective_at,
        owner=assumption_set.owner,
        description=(
            f"Sensitivity derivative of {assumption_set.assumption_set_id}@{assumption_set.version}: "
            f"{name} held at its {band.value} bound ({value!r}). Not a publishable set."
        ),
        status=AssumptionStatus.DRAFT,
        records=records,
    )


def evaluate_sensitivity(
    assumption_set: AssumptionSet,
    assumption_name: str,
    evaluate: Callable[[AssumptionSetView], SensitivityOutcome],
) -> SensitivityReport:
    """Re-run ``evaluate`` at the LOW, BASE and HIGH ends of one assumption's range."""
    record = assumption_set.record(assumption_name)
    low, high = record.sensitivity_range
    bands: Sequence[tuple[SensitivityBand, AssumptionValue]] = (
        (SensitivityBand.LOW, low),
        (SensitivityBand.BASE, record.value),
        (SensitivityBand.HIGH, high),
    )

    cases: list[SensitivityCase] = []
    for band, value in bands:
        band_set = (
            assumption_set
            if band is SensitivityBand.BASE
            else derive_band_set(assumption_set, name=assumption_name, value=value, band=band)
        )
        outcome = evaluate(AssumptionSetView(band_set))
        cases.append(
            SensitivityCase(
                band=band,
                value=value,
                assumption_version=band_set.token,
                opened_facility_ids=tuple(outcome.opened_facility_ids),
                objective_value=outcome.objective_value,
            )
        )

    base_case = next(case for case in cases if case.band is SensitivityBand.BASE)
    selections = {frozenset(case.opened_facility_ids) for case in cases}
    objectives = {case.objective_value for case in cases}

    return SensitivityReport(
        assumption_set_id=assumption_set.assumption_set_id,
        version=assumption_set.version,
        sha256=assumption_set.sha256,
        assumption_name=record.name,
        unit=record.unit,
        source=record.source,
        base_value=base_case.value,
        low_value=low,
        high_value=high,
        cases=tuple(cases),
        facility_selection_changed=len(selections) > 1,
        objective_changed=len(objectives) > 1,
    )


def sweep_sensitivity(
    assumption_set: AssumptionSet,
    evaluate: Callable[[AssumptionSetView], SensitivityOutcome],
    *,
    names: Iterable[str] | None = None,
) -> tuple[SensitivityReport, ...]:
    """Run :func:`evaluate_sensitivity` across every assumption (or a named subset)."""
    targets = tuple(names) if names is not None else assumption_set.names()
    return tuple(evaluate_sensitivity(assumption_set, name, evaluate) for name in targets)


def sensitive_assumptions(reports: Iterable[SensitivityReport]) -> tuple[SensitivityReport, ...]:
    """Just the assumptions whose stated range moved the decision."""
    return tuple(report for report in reports if report.decision_is_sensitive)
