from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, StrictBool, StrictFloat, StrictInt, StrictStr


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
    evidence_class: StrictStr
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
    layer: StrictStr
    state: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    reason: StrictStr
    evidence_class: Literal["UNAVAILABLE"] = "UNAVAILABLE"


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
    layer: Literal["roads", "intersections", "pois"]
    state: Literal["AVAILABLE", "UNAVAILABLE"]
    complete: StrictBool
    total_feature_count: StrictInt
    returned_feature_count: StrictInt
    selection_policy: StrictStr
    geojson: dict[str, Any]


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
