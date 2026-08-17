from datetime import datetime
from enum import Enum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator

# The evidence taxonomy is owned by the temporal contracts module. The API layer
# must never define a second vocabulary; it re-exports the canonical enum so
# that a non-canonical string cannot be serialised out of an API response.
from services.temporal.contracts import EvidenceClass

__all__ = [
    "DQResult",
    "DataHealthResponse",
    "DatasetAvailability",
    "DatasetListResponse",
    "DatasetRecord",
    "EvidenceClass",
    "EvidenceRecord",
    "EvidenceResponse",
    "FieldEvidence",
    "MapLayer",
    "MapLayerListResponse",
    "NetworkMetrics",
    "NetworkSnapshot",
    "NetworkSnapshotListResponse",
    "NetworkSnapshotResponse",
    "Provenance",
    "ProviderHealth",
    "ProviderState",
    "StrictContract",
    "UnavailableLayer",
    "ZoneListResponse",
    "ZoneState",
    "ZoneStateResponse",
    "ZoneStaticState",
    "ZoneSummary",
]


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class DatasetAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    EMPTY = "EMPTY"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderState(str, Enum):
    FRESH = "FRESH"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class DQResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class Provenance(StrictContract):
    evidence_class: EvidenceClass
    source: StrictStr
    source_version: StrictStr | None
    observed_at: datetime | None
    artifact_hash: StrictStr | None


class FieldEvidence(Provenance):
    value: StrictStr | StrictInt | StrictFloat | StrictBool | None
    unit: StrictStr | None = None


class DatasetRecord(Provenance):
    dataset_id: StrictStr
    provider: StrictStr
    version: StrictStr
    schema_version: StrictStr | None
    availability: DatasetAvailability
    record_count: StrictInt | None
    run_id: StrictStr | None = None


class DatasetListResponse(StrictContract):
    data: list[DatasetRecord]


class ZoneSummary(Provenance):
    zone_id: StrictStr
    resolution: StrictInt
    boundary: list[tuple[StrictFloat, StrictFloat]]


class ZoneListResponse(StrictContract):
    data: list[ZoneSummary]


class ZoneStaticState(StrictContract):
    cell_area_km2: FieldEvidence
    road_length_km: FieldEvidence
    intersection_count: FieldEvidence
    restaurant_count: FieldEvidence
    grocery_count: FieldEvidence
    commercial_poi_count: FieldEvidence
    road_density_km_per_sqkm: FieldEvidence
    intersection_density_per_sqkm: FieldEvidence


class UnavailableLayer(StrictContract):
    """A layer that carries no data yet.

    ``state`` — not ``evidence_class`` — is the availability vocabulary. There
    is no evidence to classify when there is no observation, so
    ``evidence_class`` is explicitly absent (``null``) rather than borrowing a
    value that is not a member of :class:`EvidenceClass`.
    """

    layer: StrictStr
    state: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    reason: StrictStr
    evidence_class: None = None


class ZoneState(Provenance):
    zone_id: StrictStr
    resolution: StrictInt
    boundary: list[tuple[StrictFloat, StrictFloat]]
    static: ZoneStaticState
    unavailable_dynamic_layers: list[UnavailableLayer]


class ZoneStateResponse(StrictContract):
    data: ZoneState


class NetworkMetrics(StrictContract):
    graph_vertices: StrictInt
    graph_directed_edges: StrictInt
    intersections: StrictInt
    connected_components: StrictInt
    largest_component_vertices: StrictInt


class NetworkSnapshot(Provenance):
    snapshot_id: StrictStr
    graph_version: StrictStr
    h3_resolution: StrictInt
    status: Literal["AVAILABLE"] = "AVAILABLE"
    metrics: NetworkMetrics


class NetworkSnapshotListResponse(StrictContract):
    data: list[NetworkSnapshot]


class NetworkSnapshotResponse(StrictContract):
    data: NetworkSnapshot


class MapLayer(Provenance):
    """A map layer, which may or may not have a mounted artifact behind it.

    ``state`` is the availability vocabulary. ``evidence_class`` narrows to
    ``None`` exactly when the layer is ``UNAVAILABLE``: an unmounted artifact
    produces no evidence, so it gets no evidence class instead of a made-up
    one.
    """

    layer: Literal["roads", "intersections", "pois"]
    state: Literal["AVAILABLE", "UNAVAILABLE"]
    evidence_class: EvidenceClass | None
    complete: StrictBool
    total_feature_count: StrictInt
    returned_feature_count: StrictInt
    selection_policy: StrictStr
    geojson: dict[str, Any]

    @model_validator(mode="after")
    def _availability_matches_evidence(self) -> Self:
        if self.state == "UNAVAILABLE" and self.evidence_class is not None:
            raise ValueError("An UNAVAILABLE map layer must not claim an evidence class")
        if self.state == "AVAILABLE" and self.evidence_class is None:
            raise ValueError("An AVAILABLE map layer must declare its evidence class")
        return self


class MapLayerListResponse(StrictContract):
    data: list[MapLayer]


class ProviderHealth(StrictContract):
    provider: StrictStr
    state: ProviderState
    last_successful_collection: datetime | None
    expected_freshness_seconds: StrictInt
    observed_freshness_seconds: StrictInt | None
    dq_result: DQResult
    latest_run_status: StrictStr | None
    dataset_ids: list[StrictStr]


class DataHealthResponse(StrictContract):
    data: list[ProviderHealth]
    evaluated_at: datetime


EvidenceScalar = StrictStr | StrictInt | StrictFloat | StrictBool | None


class EvidenceRecord(Provenance):
    entity_type: StrictStr
    entity_id: StrictStr
    metadata: dict[StrictStr, EvidenceScalar]


class EvidenceResponse(StrictContract):
    data: EvidenceRecord
