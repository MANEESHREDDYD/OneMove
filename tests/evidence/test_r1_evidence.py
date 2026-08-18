import json
from pathlib import Path

import pytest

from services.evidence.r1 import (
    EvidenceValidationError,
    build_r1_evidence_manifest,
    sha256_file,
    sha256_file_set,
)

CODE_SHA = "a" * 40


def _write(path: Path, value: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return sha256_file(path)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def evidence_tree(root: Path) -> None:
    official = root / "private" / "official"
    osm = official / "raw" / "osm"
    osrm = official / "raw" / "osrm"
    manifests = official / "manifests"
    gold = official / "gold"

    hashes = {
        "source_pbf_sha256": _write(osm / "southern-zone-latest.osm.pbf", b"source"),
        "clip_pbf_sha256": _write(osm / "pilot_corridor.osm.pbf", b"clip"),
        "roads_pbf_sha256": _write(osm / "pilot_roads.osm.pbf", b"roads"),
        "pois_pbf_sha256": _write(osm / "pilot_pois.osm.pbf", b"pois"),
        "gold_parquet_sha256": _write(gold / "gold_network_h3_8.parquet", b"gold"),
        "osrm_graph_file_sha256": _write(osrm / "pilot_roads.osrm", b"graph"),
    }
    hashes["osrm_graph_bundle_sha256"] = sha256_file_set([osrm / "pilot_roads.osrm"], relative_to=osrm)
    _write_json(
        osm / "manifest.json",
        {
            "provider": "osm_geofabrik",
            "source_pbf": "https://download.geofabrik.de/example.osm.pbf",
            "retrieved_at": "2026-08-13T00:00:00+00:00",
            "checksum_verified": True,
            "code_sha": CODE_SHA,
            "dq_status": "PASS",
            "osm_pbf_nodes": 10,
            "osm_highway_ways": 5,
            "pois": 2,
            "input_hashes": {"source_pbf_sha256": hashes["source_pbf_sha256"]},
            "output_hashes": {
                "clip_pbf_sha256": hashes["clip_pbf_sha256"],
                "roads_pbf_sha256": hashes["roads_pbf_sha256"],
                "pois_pbf_sha256": hashes["pois_pbf_sha256"],
            },
        },
    )
    _write_json(
        manifests / "gold_manifest.json",
        {
            "code_sha": CODE_SHA,
            "dq_status": "PASS",
            "rows": 3,
            "dataset_version": "osm-abc.code-aaa",
            "graph_version": "1.1",
            "schema_version": "1.0.0",
            "parquet_sha256": hashes["gold_parquet_sha256"],
            "graph_topology_sha256": "topology",
            "pilot_boundary_hash": "boundary",
            "sorted_cell_list_sha256": "cells",
            "input_hashes": {"roads_pbf_sha256": hashes["roads_pbf_sha256"]},
        },
    )
    _write_json(
        osrm / "benchmark.json",
        {
            "code_sha": CODE_SHA,
            "image": "osrm@sha256:test",
            "input_pbf_sha256": hashes["roads_pbf_sha256"],
            "graph_bundle_sha256": hashes["osrm_graph_bundle_sha256"],
        },
    )
    _write_json(
        manifests / "osrm_smoke_manifest.json",
        {
            "code_sha": CODE_SHA,
            "PBF_sha": hashes["roads_pbf_sha256"],
            "graph_bundle_sha256": hashes["osrm_graph_bundle_sha256"],
            "distance_m": 100.0,
            "duration_s": 20.0,
            "matrix_dimensions": "2x2",
            "finite_cells": 4,
            "null_cells": 0,
        },
    )


def test_build_r1_evidence_recomputes_hashes(tmp_path: Path) -> None:
    evidence_tree(tmp_path)

    evidence = build_r1_evidence_manifest(tmp_path, CODE_SHA)

    assert evidence["candidate_code_sha"] == CODE_SHA
    assert evidence["dq_status"] == "PASS"
    assert evidence["record_counts"]["h3_cells"] == 3
    assert evidence["routing_smoke"]["finite_cells"] == 4


def test_build_r1_evidence_rejects_stale_candidate(tmp_path: Path) -> None:
    evidence_tree(tmp_path)

    with pytest.raises(EvidenceValidationError, match="OSM manifest"):
        build_r1_evidence_manifest(tmp_path, "b" * 40)


def test_build_r1_evidence_rejects_tampered_artifact(tmp_path: Path) -> None:
    evidence_tree(tmp_path)
    (tmp_path / "private" / "official" / "gold" / "gold_network_h3_8.parquet").write_bytes(b"tampered")

    with pytest.raises(EvidenceValidationError, match="Gold hash mismatch"):
        build_r1_evidence_manifest(tmp_path, CODE_SHA)
