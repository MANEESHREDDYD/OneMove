import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.api.contracts.observatory import (
    DatasetAvailability,
    DatasetRecord,
    MapLayer,
    UnavailableLayer,
)
from services.api.core.auth import get_current_user
from services.api.main import app
from services.api.repositories.artifact_catalog import ArtifactCatalogRepository
from services.api.services.observatory import (
    PROVIDER_EVIDENCE_CLASS,
    ObservatoryService,
    get_observatory_service,
)
from services.temporal.contracts import EvidenceClass

ZONE_ID = "8860145b41fffff"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def observatory_service(tmp_path: Path) -> ObservatoryService:
    gold_path = tmp_path / "gold" / "gold_network_h3_8.parquet"
    gold_path.parent.mkdir(parents=True)
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "h3_index": ZONE_ID,
                    "h3_resolution": 8,
                    "cell_area_km2": 0.75,
                    "road_length_km": 12.5,
                    "intersection_count": 42,
                    "restaurant_count": 4,
                    "grocery_count": 3,
                    "commercial_poi_count": 7,
                    "road_density_km_per_sqkm": 16.67,
                    "intersection_density_per_sqkm": 56.0,
                }
            ]
        ),
        gold_path,
    )
    gold_hash = hashlib.sha256(gold_path.read_bytes()).hexdigest()
    write_json(
        tmp_path / "manifests" / "gold_manifest.json",
        {
            "dataset_id": "gold_network_bengaluru",
            "rows": 1,
            "h3_resolution": 8,
            "osm_source": "official-test-extract.osm.pbf",
            # Deliberately distinct values: schema identity and graph identity
            # are different facts and must never be swapped.
            "schema_name": "zonepilot_gold_network_h3",
            "schema_version": "test-schema-v9",
            "graph_version": "test-graph-v1",
            "parquet_sha256": gold_hash,
            "generated_at": "2026-08-13T11:00:00+00:00",
            "graph_metrics": {
                "graph_vertices": 100,
                "graph_directed_edges": 240,
                "intersections": 42,
                "connected_components": 1,
                "largest_component_vertices": 100,
            },
        },
    )
    write_json(
        tmp_path / "manifests" / "OFFICIAL_DAILY_MANIFEST_2026-08-13.json",
        {
            "runs": [
                {
                    "run_id": "weather-run",
                    "provider": "openmeteo",
                    "dataset": "weather_forecast_snapshots",
                    "status": "COMPLETED",
                    "completed_at": "2026-08-13T11:30:00+00:00",
                    "records_written": 144,
                    "raw_hash": "weather-hash",
                    "missing_intervals": 0,
                },
                {
                    "run_id": "traffic-run",
                    "provider": "tomtom",
                    "dataset": "traffic_flow",
                    "status": "FAILED",
                    "completed_at": "2026-08-13T11:45:00+00:00",
                    "records_written": 0,
                    "error_code": "UPSTREAM_FAILURE",
                },
            ]
        },
    )
    write_json(
        tmp_path / "raw" / "osm" / "manifest.json",
        {
            "timestamp": "2026-08-13T11:00:00+00:00",
            "provider": "osm_geofabrik",
            "source_version": "osm-source-v1",
        },
    )
    write_json(
        tmp_path / "raw" / "osm" / "pilot_roads.geojson",
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[77.61, 12.93], [77.62, 12.94], [77.63, 12.93]],
                    },
                    "properties": {"highway": "primary"},
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[77.62, 12.92], [77.62, 12.94]],
                    },
                    "properties": {"highway": "secondary"},
                },
            ],
        },
    )
    write_json(
        tmp_path / "raw" / "osm" / "silver_pois.geojson",
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [77.62, 12.94]},
                    "properties": {"amenity": "restaurant"},
                }
            ],
        },
    )
    write_json(
        tmp_path / "manifests" / "osrm_smoke_manifest.json",
        {
            "graph_bundle_sha256": "graph-sha",
            "OSRM_image_digest": "image-digest",
            "generated_at": "2026-08-13T11:10:00+00:00",
        },
    )
    network_path = tmp_path / "raw" / "osrm" / "pilot_roads.osrm"
    network_path.parent.mkdir(parents=True)
    network_path.write_bytes(b"network")

    return ObservatoryService(
        ArtifactCatalogRepository(tmp_path),
        now=lambda: datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
    )


def test_catalog_exposes_versioned_real_artifacts(observatory_service: ObservatoryService) -> None:
    datasets = observatory_service.list_datasets().data
    assert [(item.dataset_id, item.availability.value) for item in datasets] == [
        ("gold_network_bengaluru", "AVAILABLE"),
        ("openmeteo:weather_forecast_snapshots", "AVAILABLE"),
        ("tomtom:traffic_flow", "FAILED"),
    ]
    assert datasets[0].artifact_hash == datasets[0].version


def test_zone_state_attaches_evidence_to_every_static_field(observatory_service: ObservatoryService) -> None:
    state = observatory_service.get_zone_state(ZONE_ID).data
    assert state.static.road_length_km.value == 12.5
    assert state.static.road_length_km.evidence_class == "PUBLIC_GEOGRAPHIC"
    assert state.static.intersection_count.artifact_hash == state.artifact_hash
    assert {layer.layer for layer in state.unavailable_dynamic_layers} == {"traffic", "weather"}


def test_data_health_is_computed_from_runs_and_slas(observatory_service: ObservatoryService) -> None:
    health = {item.provider: item for item in observatory_service.data_health().data}
    assert health["openmeteo"].state.value == "FRESH"
    assert health["openmeteo"].observed_freshness_seconds == 30 * 60
    assert health["tomtom"].state.value == "UNAVAILABLE"
    assert health["tomtom"].dq_result.value == "UNKNOWN"
    assert health["osm"].state.value == "FRESH"
    assert health["osrm"].state.value == "FRESH"


def test_evidence_lookup_returns_manifest_lineage(observatory_service: ObservatoryService) -> None:
    evidence = observatory_service.get_evidence("network", "graph-sha").data
    assert evidence.artifact_hash == "graph-sha"
    assert evidence.metadata["graph_vertices"] == 100


def test_map_layers_render_real_bounded_osm_evidence(observatory_service: ObservatoryService) -> None:
    layers = {item.layer: item for item in observatory_service.map_layers().data}
    assert set(layers) == {"roads", "intersections", "pois"}
    assert layers["roads"].state == "AVAILABLE"
    assert layers["roads"].returned_feature_count == 2
    assert layers["intersections"].returned_feature_count == 1
    assert layers["pois"].returned_feature_count == 1
    assert layers["pois"].artifact_hash


def test_protected_routes_return_contracts(observatory_service: ObservatoryService) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
    }
    app.dependency_overrides[get_observatory_service] = lambda: observatory_service
    try:
        with TestClient(app) as client:
            zones = client.get("/api/v1/zones")
            assert zones.status_code == 200
            assert zones.json()["data"][0]["zone_id"] == ZONE_ID

            state = client.get(f"/api/v1/zones/{ZONE_ID}/state")
            assert state.status_code == 200
            assert state.json()["data"]["static"]["road_length_km"]["value"] == 12.5

            health = client.get("/api/v1/data-health")
            assert health.status_code == 200
            assert {item["state"] for item in health.json()["data"]} <= {"FRESH", "DEGRADED", "STALE", "UNAVAILABLE"}

            map_layers = client.get("/api/v1/network/map-layers")
            assert map_layers.status_code == 200
            assert {item["layer"] for item in map_layers.json()["data"]} == {"roads", "intersections", "pois"}
    finally:
        app.dependency_overrides.clear()


def test_invalid_h3_uses_standard_error_contract(observatory_service: ObservatoryService) -> None:
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user",
        "workspace_id": "00000000-0000-0000-0000-000000000001",
    }
    app.dependency_overrides[get_observatory_service] = lambda: observatory_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/zones/not-an-h3/state", headers={"x-request-id": "request-123"})
        assert response.status_code == 422
        assert response.json()["error"] == {
            "code": "INVALID_ARGUMENT",
            "message": "Zone ID must be a valid H3 cell identifier",
            "retryable": False,
            "details": {},
            "request_id": "request-123",
            # F-025: the canonical envelope carries trace_id for correlation.
            "trace_id": "request-123",
        }
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/datasets",
        "/api/v1/zones",
        f"/api/v1/zones/{ZONE_ID}/state",
        "/api/v1/data-health",
        "/api/v1/network/snapshots",
        "/api/v1/network/map-layers",
        "/api/v1/evidence/zone/8860145b41fffff",
        "/api/v1/scenarios/example",
        "/api/v1/optimizations/example",
    ],
)
def test_observatory_routes_require_authentication(path: str) -> None:
    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


# --- Evidence taxonomy -------------------------------------------------------


def test_every_provider_maps_to_a_canonical_evidence_class() -> None:
    assert set(PROVIDER_EVIDENCE_CLASS.values()) <= set(EvidenceClass)
    assert PROVIDER_EVIDENCE_CLASS["openmeteo"] is EvidenceClass.PUBLIC_OFFICIAL
    assert PROVIDER_EVIDENCE_CLASS["ondc"] is EvidenceClass.PUBLIC_OFFICIAL


def test_served_evidence_classes_are_all_canonical(observatory_service: ObservatoryService) -> None:
    """No API response may carry a string outside the canonical taxonomy."""
    emitted: list[EvidenceClass | None] = []
    emitted.extend(item.evidence_class for item in observatory_service.list_datasets().data)
    emitted.extend(item.evidence_class for item in observatory_service.list_zones().data)
    emitted.extend(item.evidence_class for item in observatory_service.list_network_snapshots().data)
    emitted.extend(item.evidence_class for item in observatory_service.map_layers().data)

    zone = observatory_service.get_zone_state(ZONE_ID).data
    emitted.append(zone.evidence_class)
    emitted.extend(getattr(zone.static, name).evidence_class for name in type(zone.static).model_fields)
    emitted.extend(layer.evidence_class for layer in zone.unavailable_dynamic_layers)

    assert emitted, "fixture produced no evidence-bearing records"
    assert all(value is None or isinstance(value, EvidenceClass) for value in emitted)
    assert "OFFICIAL_API_REAL" not in {str(getattr(value, "value", value)) for value in emitted}
    assert "UNAVAILABLE" not in {str(getattr(value, "value", value)) for value in emitted}


def test_openmeteo_dataset_is_public_official(observatory_service: ObservatoryService) -> None:
    datasets = {item.dataset_id: item for item in observatory_service.list_datasets().data}
    weather = datasets["openmeteo:weather_forecast_snapshots"]
    assert weather.evidence_class is EvidenceClass.PUBLIC_OFFICIAL
    assert datasets["tomtom:traffic_flow"].evidence_class is EvidenceClass.PROVIDER_ESTIMATED


def _dataset_record(evidence_class: object) -> DatasetRecord:
    return DatasetRecord(
        dataset_id="d",
        provider="p",
        version="v",
        schema_version=None,
        availability=DatasetAvailability.AVAILABLE,
        record_count=1,
        evidence_class=evidence_class,
        source="s",
        source_version=None,
        observed_at=None,
        artifact_hash=None,
    )


@pytest.mark.parametrize("rejected", ["OFFICIAL_API_REAL", "UNAVAILABLE", "NOT_A_CLASS", None])
def test_provenance_contract_rejects_non_canonical_evidence_class(rejected: object) -> None:
    """The type system, not convention, is what blocks a third vocabulary."""
    with pytest.raises(ValidationError):
        _dataset_record(rejected)


def test_provenance_contract_accepts_the_canonical_enum() -> None:
    assert _dataset_record(EvidenceClass.PUBLIC_OFFICIAL).evidence_class is EvidenceClass.PUBLIC_OFFICIAL


def test_unavailable_layer_has_no_evidence_class() -> None:
    """`UNAVAILABLE` is an availability state, carried by `state`, not evidence."""
    layer = UnavailableLayer(layer="traffic", reason="no observation joined to this cell")
    assert layer.state == "UNAVAILABLE"
    assert layer.evidence_class is None
    assert layer.model_dump()["evidence_class"] is None


def test_unavailable_dynamic_layers_do_not_claim_evidence(observatory_service: ObservatoryService) -> None:
    zone = observatory_service.get_zone_state(ZONE_ID).data
    assert zone.unavailable_dynamic_layers
    for layer in zone.unavailable_dynamic_layers:
        assert layer.state == "UNAVAILABLE"
        assert layer.evidence_class is None


def test_map_layer_availability_and_evidence_class_must_agree() -> None:
    base = {
        "layer": "roads",
        "complete": True,
        "total_feature_count": 0,
        "returned_feature_count": 0,
        "selection_policy": "policy",
        "geojson": {"type": "FeatureCollection", "features": []},
        "source": "s",
        "source_version": None,
        "observed_at": None,
        "artifact_hash": None,
    }
    with pytest.raises(ValidationError):
        MapLayer(state="UNAVAILABLE", evidence_class=EvidenceClass.PUBLIC_GEOGRAPHIC, **base)
    with pytest.raises(ValidationError):
        MapLayer(state="AVAILABLE", evidence_class=None, **base)
    assert MapLayer(state="UNAVAILABLE", evidence_class=None, **base).evidence_class is None


def test_unmounted_map_layers_report_availability_without_evidence(
    observatory_service: ObservatoryService, tmp_path: Path
) -> None:
    (tmp_path / "raw" / "osm" / "pilot_roads.geojson").unlink()
    (tmp_path / "raw" / "osm" / "silver_pois.geojson").unlink()

    layers = {item.layer: item for item in observatory_service.map_layers().data}
    assert set(layers) == {"roads", "intersections", "pois"}
    for layer in layers.values():
        assert layer.state == "UNAVAILABLE"
        assert layer.evidence_class is None


# --- Schema identity ---------------------------------------------------------


def test_gold_schema_version_is_schema_identity_not_graph_version(
    observatory_service: ObservatoryService,
) -> None:
    """`schema_version` must carry the Gold manifest's schema identity.

    It used to be populated from `graph_version`, which identifies the road
    graph the rows were derived from. This test fails if the two are swapped
    again, because the fixture gives them deliberately different values.
    """
    gold = next(
        item for item in observatory_service.list_datasets().data if item.dataset_id == "gold_network_bengaluru"
    )
    snapshot = observatory_service.list_network_snapshots().data[0]

    assert gold.schema_version == "test-schema-v9"
    assert snapshot.graph_version == "test-graph-v1"
    assert gold.schema_version != snapshot.graph_version


def test_gold_schema_version_absent_when_manifest_omits_it(
    observatory_service: ObservatoryService, tmp_path: Path
) -> None:
    manifest_path = tmp_path / "manifests" / "gold_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["schema_version"]
    write_json(manifest_path, manifest)

    gold = next(
        item for item in observatory_service.list_datasets().data if item.dataset_id == "gold_network_bengaluru"
    )
    assert gold.schema_version is None
