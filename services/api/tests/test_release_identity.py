import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.api.core.auth import get_current_user
from services.api.main import app
from services.api.repositories.artifact_catalog import ArtifactCatalogRepository
from services.api.services.release_identity import (
    ReleaseIdentityService,
    ReleaseIdentityUnavailable,
    get_release_identity_service,
)

CODE_SHA = "a" * 40
SCHEMA_VERSION = "1.0.0"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture
def release_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReleaseIdentityService:
    gold_path = tmp_path / "gold" / "gold_network_h3_8.parquet"
    gold_path.parent.mkdir(parents=True)
    gold_path.write_bytes(b"verified-gold")

    osrm_dir = tmp_path / "raw" / "osrm"
    osrm_dir.mkdir(parents=True)
    (osrm_dir / "pilot_roads.osrm").write_bytes(b"graph-base")
    (osrm_dir / "pilot_roads.osrm.edges").write_bytes(b"graph-edges")

    repository = ArtifactCatalogRepository(tmp_path)
    graph_sha = repository.osrm_graph_bundle_hash()
    gold_sha = hashlib.sha256(gold_path.read_bytes()).hexdigest()
    write_json(
        tmp_path / "manifests" / "gold_manifest.json",
        {
            "code_sha": CODE_SHA,
            "dataset_id": "gold_network_bengaluru",
            "dataset_version": "osm-abc.code-aaa",
            "schema_version": SCHEMA_VERSION,
            "graph_version": "1.1.0",
            "graph_topology_sha256": "b" * 64,
            "parquet_sha256": gold_sha,
            "input_hashes": {"roads_pbf_sha256": "d" * 64},
            "rows": 3,
            "dq_status": "PASS",
        },
    )
    write_json(
        tmp_path / "raw" / "osrm" / "benchmark.json",
        {
            "code_sha": CODE_SHA,
            "input_pbf_sha256": "d" * 64,
            "graph_bundle_sha256": graph_sha,
            "dq_status": "PASS",
        },
    )
    write_json(
        tmp_path / "manifests" / "osrm_smoke_manifest.json",
        {
            "code_sha": CODE_SHA,
            "graph_bundle_sha256": graph_sha,
            "PBF_sha": "d" * 64,
            "distance_m": 1_000.0,
            "duration_s": 120.0,
            "finite_cells": 4,
            "null_cells": 0,
            "dq_status": "PASS",
        },
    )

    monkeypatch.setenv("ZONEPILOT_APP_VERSION", "1.5.1")
    monkeypatch.setenv("ZONEPILOT_GIT_SHA", CODE_SHA)
    monkeypatch.setenv("ZONEPILOT_SCHEMA_VERSION", SCHEMA_VERSION)
    return ReleaseIdentityService(repository)


def test_release_identity_recomputes_gold_and_graph_hashes(
    release_service: ReleaseIdentityService,
) -> None:
    identity = release_service.get_release_identity().data
    assert identity.app_version == "1.5.1"
    assert identity.git_sha == CODE_SHA
    assert identity.schema_version == SCHEMA_VERSION
    assert identity.gold.dataset_id == "gold_network_bengaluru"
    assert identity.gold.artifact_sha256 == release_service.repository.gold_artifact_hash()
    assert identity.graph.bundle_sha256 == release_service.repository.osrm_graph_bundle_hash()
    assert identity.graph.topology_sha256 == "b" * 64


def test_release_identity_rejects_missing_or_placeholder_config(
    release_service: ReleaseIdentityService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ZONEPILOT_APP_VERSION")
    with pytest.raises(ReleaseIdentityUnavailable):
        release_service.get_release_identity()

    monkeypatch.setenv("ZONEPILOT_APP_VERSION", "unknown")
    with pytest.raises(ReleaseIdentityUnavailable):
        release_service.get_release_identity()


def test_release_identity_rejects_stale_or_tampered_artifacts(
    release_service: ReleaseIdentityService,
) -> None:
    release_service.repository.gold_artifact_path().write_bytes(b"tampered")
    with pytest.raises(ReleaseIdentityUnavailable):
        release_service.get_release_identity()


def test_release_identity_rejects_tampered_graph_bundle(
    release_service: ReleaseIdentityService,
) -> None:
    graph_path = release_service.repository.root / "raw" / "osrm" / "pilot_roads.osrm"
    graph_path.write_bytes(b"tampered")
    with pytest.raises(ReleaseIdentityUnavailable):
        release_service.get_release_identity()


def test_release_identity_rejects_manifest_release_mismatch(
    release_service: ReleaseIdentityService,
) -> None:
    manifest_path = release_service.repository.root / "manifests" / "gold_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["code_sha"] = "c" * 40
    write_json(manifest_path, manifest)
    with pytest.raises(ReleaseIdentityUnavailable):
        release_service.get_release_identity()


def test_release_identity_rejects_unlinked_graph_evidence(
    release_service: ReleaseIdentityService,
) -> None:
    manifest_path = release_service.repository.root / "manifests" / "osrm_smoke_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["PBF_sha"] = "e" * 64
    write_json(manifest_path, manifest)
    with pytest.raises(ReleaseIdentityUnavailable):
        release_service.get_release_identity()


def test_version_route_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/version")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_version_route_returns_only_strict_release_identity(
    release_service: ReleaseIdentityService,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test-user"}
    app.dependency_overrides[get_release_identity_service] = lambda: release_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/version")
        assert response.status_code == 200
        assert set(response.json()) == {"data"}
        assert set(response.json()["data"]) == {
            "app_version",
            "git_sha",
            "schema_version",
            "gold",
            "graph",
        }
        serialized = response.text.lower()
        assert "path" not in serialized
        assert "secret" not in serialized
        assert "placeholder" not in serialized
    finally:
        app.dependency_overrides.clear()


def test_version_route_fails_closed_without_leaking_artifact_location(tmp_path: Path) -> None:
    service = ReleaseIdentityService(
        ArtifactCatalogRepository(tmp_path),
        {
            "ZONEPILOT_APP_VERSION": "1.5.1",
            "ZONEPILOT_GIT_SHA": CODE_SHA,
            "ZONEPILOT_SCHEMA_VERSION": SCHEMA_VERSION,
        },
    )
    app.dependency_overrides[get_current_user] = lambda: {"sub": "test-user"}
    app.dependency_overrides[get_release_identity_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/version", headers={"x-request-id": "release-check"})
        assert response.status_code == 503
        assert response.json()["error"] == {
            "code": "RELEASE_IDENTITY_UNAVAILABLE",
            "message": "Release identity is unavailable or could not be verified.",
            "retryable": True,
            "details": {},
            "request_id": "release-check",
            # F-025: the canonical envelope carries trace_id for correlation.
            "trace_id": "release-check",
        }
        assert str(tmp_path) not in response.text
    finally:
        app.dependency_overrides.clear()
