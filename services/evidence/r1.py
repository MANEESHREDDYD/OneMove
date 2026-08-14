from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EvidenceValidationError(ValueError):
    """Raised when an R1 artifact cannot support a release claim."""


def candidate_code_sha() -> str:
    """Return the exact candidate SHA, preferring the CI-pinned value."""
    pinned = os.environ.get("ZONEPILOT_CANDIDATE_SHA", "").strip()
    if pinned:
        if re.fullmatch(r"[0-9a-f]{40}", pinned) is None:
            raise EvidenceValidationError("ZONEPILOT_CANDIDATE_SHA must be a full lowercase Git SHA")
        return pinned

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    )
    sha = result.stdout.strip()
    if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise EvidenceValidationError("Unable to resolve a full candidate Git SHA")
    return sha


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_file_set(paths: list[Path], *, relative_to: Path) -> str:
    """Hash file names and bytes so a multi-file artifact has one identity."""
    if not paths:
        raise EvidenceValidationError("Cannot hash an empty artifact file set")
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(relative_to).as_posix()):
        relative_name = path.relative_to(relative_to).as_posix().encode("utf-8")
        digest.update(relative_name)
        digest.update(b"\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise EvidenceValidationError(f"Required evidence is missing: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceValidationError(f"Invalid evidence JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise EvidenceValidationError(f"Evidence must be an object: {path.name}")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceValidationError(message)


def build_r1_evidence_manifest(data_root: Path, code_sha: str) -> dict[str, Any]:
    """Verify the R1 geospatial chain and return a sanitized evidence manifest."""
    official = data_root / "private" / "official"
    osm_dir = official / "raw" / "osm"
    osrm_dir = official / "raw" / "osrm"
    manifests_dir = official / "manifests"
    gold_dir = official / "gold"

    osm = _load_json(osm_dir / "manifest.json")
    gold = _load_json(manifests_dir / "gold_manifest.json")
    osrm_build = _load_json(osrm_dir / "benchmark.json")
    osrm_smoke = _load_json(manifests_dir / "osrm_smoke_manifest.json")

    source_pbf = osm_dir / "southern-zone-latest.osm.pbf"
    clip_pbf = osm_dir / "pilot_corridor.osm.pbf"
    roads_pbf = osm_dir / "pilot_roads.osm.pbf"
    pois_pbf = osm_dir / "pilot_pois.osm.pbf"
    gold_parquet = gold_dir / "gold_network_h3_8.parquet"
    osrm_graph_files = [path for path in osrm_dir.glob("pilot_roads.osrm*") if path.is_file()]

    actual_hashes = {
        "source_pbf_sha256": sha256_file(source_pbf),
        "clip_pbf_sha256": sha256_file(clip_pbf),
        "roads_pbf_sha256": sha256_file(roads_pbf),
        "pois_pbf_sha256": sha256_file(pois_pbf),
        "gold_parquet_sha256": sha256_file(gold_parquet),
        "osrm_graph_bundle_sha256": sha256_file_set(osrm_graph_files, relative_to=osrm_dir),
    }

    osm_outputs = osm.get("output_hashes", {})
    _require(osm.get("code_sha") == code_sha, "OSM manifest is not tied to the candidate SHA")
    _require(osm.get("dq_status") == "PASS", "OSM data quality did not pass")
    _require(osm.get("osm_pbf_nodes", 0) > 0, "OSM road extract contains no nodes")
    _require(osm.get("osm_highway_ways", 0) > 0, "OSM road extract contains no ways")
    _require(osm.get("pois", 0) > 0, "OSM POI extract contains no POIs")
    for name in ("clip_pbf_sha256", "roads_pbf_sha256", "pois_pbf_sha256"):
        _require(osm_outputs.get(name) == actual_hashes[name], f"OSM output hash mismatch: {name}")
    _require(
        osm.get("input_hashes", {}).get("source_pbf_sha256") == actual_hashes["source_pbf_sha256"],
        "Geofabrik source PBF hash mismatch",
    )

    _require(gold.get("code_sha") == code_sha, "Gold manifest is not tied to the candidate SHA")
    _require(gold.get("dq_status") == "PASS", "Gold data quality did not pass")
    _require(gold.get("rows", 0) > 0, "Gold dataset contains no rows")
    _require(
        gold.get("input_hashes", {}).get("roads_pbf_sha256") == actual_hashes["roads_pbf_sha256"],
        "Gold input does not match the road extract",
    )
    _require(gold.get("parquet_sha256") == actual_hashes["gold_parquet_sha256"], "Gold hash mismatch")
    _require(gold.get("graph_topology_sha256"), "Canonical graph topology hash is missing")

    _require(osrm_build.get("code_sha") == code_sha, "OSRM build is not tied to the candidate SHA")
    _require(
        osrm_build.get("input_pbf_sha256") == actual_hashes["roads_pbf_sha256"],
        "OSRM input does not match the road extract",
    )
    _require(
        osrm_build.get("graph_bundle_sha256") == actual_hashes["osrm_graph_bundle_sha256"],
        "OSRM graph bundle hash mismatch",
    )
    _require(osrm_smoke.get("code_sha") == code_sha, "OSRM smoke test is not tied to the candidate SHA")
    _require(
        osrm_smoke.get("graph_bundle_sha256") == actual_hashes["osrm_graph_bundle_sha256"],
        "OSRM smoke graph bundle mismatch",
    )
    _require(osrm_smoke.get("PBF_sha") == actual_hashes["roads_pbf_sha256"], "OSRM smoke PBF mismatch")
    _require(osrm_smoke.get("distance_m", 0) > 0, "OSRM route has no positive distance")
    _require(osrm_smoke.get("duration_s", 0) > 0, "OSRM route has no positive duration")
    _require(osrm_smoke.get("finite_cells", 0) > 0, "OSRM matrix has no finite cells")
    _require(osrm_smoke.get("null_cells") == 0, "OSRM matrix contains unreachable cells")

    return {
        "schema_name": "zonepilot_r1_evidence",
        "schema_version": "1.0.0",
        "evidence_class": "PUBLIC_GEOGRAPHIC",
        "candidate_code_sha": code_sha,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": osm.get("provider"),
            "url": osm.get("source_pbf"),
            "retrieved_at": osm.get("retrieved_at"),
            "checksum_verified": osm.get("checksum_verified") is True,
        },
        "versions": {
            "dataset_version": gold.get("dataset_version"),
            "graph_version": gold.get("graph_version"),
            "gold_schema_version": gold.get("schema_version"),
            "osrm_image": osrm_build.get("image"),
        },
        "record_counts": {
            "osm_nodes": osm.get("osm_pbf_nodes"),
            "osm_highway_ways": osm.get("osm_highway_ways"),
            "pois": osm.get("pois"),
            "h3_cells": gold.get("rows"),
        },
        "hashes": {
            **actual_hashes,
            "boundary_sha256": gold.get("pilot_boundary_hash"),
            "h3_cell_list_sha256": gold.get("sorted_cell_list_sha256"),
            "graph_topology_sha256": gold.get("graph_topology_sha256"),
        },
        "routing_smoke": {
            "distance_m": osrm_smoke.get("distance_m"),
            "duration_s": osrm_smoke.get("duration_s"),
            "matrix_dimensions": osrm_smoke.get("matrix_dimensions"),
            "finite_cells": osrm_smoke.get("finite_cells"),
            "null_cells": osrm_smoke.get("null_cells"),
        },
        "dq_status": "PASS",
        "stages": [
            "GEOFABRIK_DOWNLOAD",
            "CHECKSUM_VERIFY",
            "PILOT_CLIP",
            "CANONICAL_GRAPH",
            "H3_R8",
            "POI",
            "GOLD",
            "OSRM_BUILD",
            "ROUTE",
            "MATRIX",
            "MANIFEST_AUDIT",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and publish sanitized ZonePilot R1 evidence")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("ZONEPILOT_DATA_ROOT", "data_root")),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--code-sha", default=None)
    args = parser.parse_args()

    evidence = build_r1_evidence_manifest(args.data_root, args.code_sha or candidate_code_sha())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
