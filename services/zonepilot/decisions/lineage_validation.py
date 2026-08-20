"""Validate decision lineage against canonical sources (F-005).

A caller may state a facility id, a graph version or an OSRM bundle hash. Stating
one is not evidence that it exists. An independent certifier posted invented
facilities, an invented hash and 100% coverage and received a persisted decision,
because the API required those fields without ever resolving them.

Every value here is either resolved against a canonical artifact or reported
UNVERIFIED. Nothing is accepted merely because it is well-formed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from services.zonepilot.optimization.r1_catalog import default_data_root

#: Recorded against each lineage field so a reader can tell checked from unchecked.
VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"
MISMATCH = "MISMATCH"


class LineageValidationUnavailable(RuntimeError):
    """The canonical artifact needed to check a claim is not available.

    Raised rather than silently downgrading to UNVERIFIED, so a missing artifact
    is an explicit dependency failure instead of a quiet loss of rigour.
    """


@dataclass
class LineageVerdict:
    """Outcome of checking caller-supplied lineage against canonical sources."""

    verified: dict[str, str] = field(default_factory=dict)
    rejections: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.rejections


def canonical_facility_ids() -> frozenset[str]:
    """Facility identifiers present in the authentic travel matrix."""
    path = default_data_root() / "private" / "official" / "gold" / "r1_osrm_travel_matrix.json"
    if not path.is_file():
        raise LineageValidationUnavailable(
            "MATRIX_UNAVAILABLE: the authentic travel matrix is required to resolve facility identifiers."
        )
    doc = json.loads(path.read_text(encoding="utf-8"))
    ids = doc.get("facility_ids") or []
    if not ids:
        raise LineageValidationUnavailable("MATRIX_UNAVAILABLE: travel matrix contains no facility identifiers.")
    return frozenset(str(i) for i in ids)


def canonical_manifest() -> dict[str, Any]:
    path = default_data_root() / "private" / "official" / "manifests" / "gold_manifest.json"
    if not path.is_file():
        raise LineageValidationUnavailable(
            "MANIFEST_UNAVAILABLE: the gold manifest is required to resolve graph and bundle identity."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def validate_operator_lineage(
    *,
    opened_facilities: list[str],
    graph_version: str | None,
    osrm_bundle_hash: str | None,
    network_version: str | None = None,
    dataset_version: str | None = None,
    feature_snapshot_hash: str | None = None,
    solver_version: str | None = None,
) -> LineageVerdict:
    """Resolve operator-supplied lineage against canonical artifacts.

    Facility identifiers are REJECTED when unresolvable: an operator recording a
    decision about facilities that do not exist is a mistake worth surfacing, not a
    nuance to record.

    Version and hash claims are not rejected, because an operator may legitimately
    describe a decision taken against an older graph. They are marked VERIFIED,
    MISMATCH or UNVERIFIED so a reader is never left guessing which.
    """
    verdict = LineageVerdict()

    known = canonical_facility_ids()
    unknown = sorted({f for f in opened_facilities if f not in known})
    if unknown:
        verdict.rejections.append(
            f"opened_facilities contains identifiers absent from the canonical facility catalog: {', '.join(unknown)}"
        )
    else:
        verdict.verified["opened_facilities"] = VERIFIED

    manifest = canonical_manifest()

    if graph_version:
        canonical_graph = str(manifest.get("graph_version") or "")
        verdict.verified["graph_version"] = (
            VERIFIED if canonical_graph and graph_version == canonical_graph else MISMATCH
        )

    if network_version:
        canonical_network = str(manifest.get("dataset_id") or manifest.get("schema_name") or "")
        verdict.verified["network_version"] = (
            VERIFIED if canonical_network and network_version == canonical_network else MISMATCH
        )

    if dataset_version:
        canonical_dataset = str(manifest.get("dataset_version") or "")
        verdict.verified["dataset_version"] = (
            VERIFIED if canonical_dataset and dataset_version == canonical_dataset else MISMATCH
        )

    if feature_snapshot_hash:
        canonical_feature = str(manifest.get("parquet_sha256") or manifest.get("pilot_boundary_hash") or "")
        verdict.verified["feature_snapshot_hash"] = (
            VERIFIED if canonical_feature and feature_snapshot_hash == canonical_feature else MISMATCH
        )

    if solver_version:
        from services.zonepilot.release import current_release_sha
        canonical_solver = current_release_sha()
        verdict.verified["solver_version"] = (
            VERIFIED if canonical_solver and solver_version == canonical_solver else MISMATCH
        )

    if osrm_bundle_hash:
        canonical_hash = str(manifest.get("osrm_bundle_sha256") or manifest.get("osrm_table_sha256") or "")
        if not canonical_hash:
            verdict.verified["osrm_bundle_hash"] = UNVERIFIED
        else:
            verdict.verified["osrm_bundle_hash"] = VERIFIED if osrm_bundle_hash == canonical_hash else MISMATCH

    return verdict


def operator_claims(
    *,
    objective_value: int | None,
    expected_travel_seconds: int | None,
    p95_travel_seconds: int | None,
    coverage_basis_points: int | None,
) -> dict[str, Any]:
    """Package operator-supplied figures as explicitly non-authoritative.

    These never reach the solver-derived columns. evidence_class is UNVERIFIED --
    not DERIVED, not OBSERVED -- so no reader can mistake a typed-in coverage
    figure for a computed one.
    """
    claims: dict[str, Any] = {}
    for name, value in (
        ("objective_value", objective_value),
        ("expected_travel_seconds", expected_travel_seconds),
        ("p95_travel_seconds", p95_travel_seconds),
        ("coverage_basis_points", coverage_basis_points),
    ):
        if value is not None:
            claims[name] = {"value": value, "evidence_class": UNVERIFIED, "source": "operator_supplied"}
    return claims
