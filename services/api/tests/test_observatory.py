import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app
from services.api.repositories.artifact_catalog import ArtifactCatalogRepository
from services.api.services.observatory import ObservatoryService, get_observatory_service

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
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test-user"}
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
            assert {item["state"] for item in health.json()["data"]} <= {
                "FRESH", "DEGRADED", "STALE", "UNAVAILABLE"
            }

            map_layers = client.get("/api/v1/network/map-layers")
            assert map_layers.status_code == 200
            assert {item["layer"] for item in map_layers.json()["data"]} == {
                "roads", "intersections", "pois"
            }
    finally:
        app.dependency_overrides.clear()


def test_invalid_h3_uses_standard_error_contract(observatory_service: ObservatoryService) -> None:
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test-user"}
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
