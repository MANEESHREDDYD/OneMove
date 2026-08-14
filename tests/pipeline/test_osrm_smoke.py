import json
import math
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from services.evidence.r1 import candidate_code_sha, sha256_file, sha256_file_set

OSRM_IMAGE = "osrm/osrm-backend@sha256:af5d4a83fb90086a43b1ae2ca22872e6768766ad5fcbb07a29ff90ec644ee409"
DATA_ROOT = os.environ.get("ZONEPILOT_DATA_ROOT", os.path.join(os.getcwd(), "data_root"))
OSRM_DIR = os.path.join(DATA_ROOT, "private", "official", "raw", "osrm")
MANIFESTS_DIR = os.path.join(DATA_ROOT, "private", "official", "manifests")


@pytest.mark.r1_evidence
def test_osrm_smoke_server():
    graph_path = os.path.join(OSRM_DIR, "pilot_roads.osrm")
    pbf_path = os.path.join(DATA_ROOT, "private", "official", "raw", "osm", "pilot_roads.osm.pbf")
    
    if not os.path.exists(graph_path):
        pytest.fail("OSRM graph pilot_roads.osrm is missing. Required for canonical test.")
        
    container_name = "zonepilot_osrm_test"
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
    
    cmd = [
        "docker", "run", "-d", "--name", container_name,
        "-p", "5000:5000",
        "-v", f"{OSRM_DIR}:/data",
        OSRM_IMAGE, "osrm-routed", "--algorithm", "mld", "/data/pilot_roads.osrm"
    ]
    subprocess.run(cmd, check=True)
    
    try:
        origin = "77.63,12.91"
        dest = "77.64,12.92"
        route_url = f"http://localhost:5000/route/v1/driving/{origin};{dest}?overview=false"
        deadline = time.monotonic() + 30
        with httpx.Client() as client:
            while True:
                try:
                    res_route = client.get(route_url, timeout=2.0)
                    if res_route.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= deadline:
                    pytest.fail("OSRM did not become ready within 30 seconds")
                time.sleep(0.5)

            # 1. Route Request
            assert res_route.status_code == 200
            route_data = res_route.json()
            assert route_data.get("code") == "Ok"

            dist = route_data["routes"][0]["distance"]
            dur = route_data["routes"][0]["duration"]
            assert dist > 0
            assert dur > 0
            assert math.isfinite(dist)
            assert math.isfinite(dur)

            # 2. Table Request
            coords = "77.63,12.91;77.64,12.92;77.62,12.90"
            table_url = f"http://localhost:5000/table/v1/driving/{coords}"

            res_table = client.get(table_url, timeout=5.0)
        assert res_table.status_code == 200
        table_data = res_table.json()
        assert table_data.get("code") == "Ok"
        
        sources = table_data.get("sources", [])
        destinations = table_data.get("destinations", [])
        durations = table_data.get("durations", [])
        
        assert len(sources) == 3
        assert len(destinations) == 3
        
        finite_cells = 0
        null_cells = 0
        for row in durations:
            for cell in row:
                if cell is None:
                    null_cells += 1
                elif math.isfinite(cell):
                    finite_cells += 1
                    
        assert finite_cells == 9
        assert null_cells == 0
        
        # 3. Write Sanitized Manifest
        os.makedirs(MANIFESTS_DIR, exist_ok=True)
        
        graph_files = [path for path in Path(OSRM_DIR).glob("pilot_roads.osrm*") if path.is_file()]
        graph_bundle_sha = sha256_file_set(graph_files, relative_to=Path(OSRM_DIR))
            
        pbf_sha = "missing"
        if os.path.exists(pbf_path):
            pbf_sha = sha256_file(Path(pbf_path))

        manifest = {
            "schema_name": "zonepilot_osrm_smoke_manifest",
            "schema_version": "1.0.0",
            "code_sha": candidate_code_sha(),
            "PBF_sha": pbf_sha,
            "OSRM_image_digest": "af5d4a83fb90086a43b1ae2ca22872e6768766ad5fcbb07a29ff90ec644ee409",
            "profile": "default car.lua from the pinned OSRM image",
            "graph_file_count": len(graph_files),
            "graph_bundle_sha256": graph_bundle_sha,
            "origin": origin,
            "destination": dest,
            "distance_m": dist,
            "duration_s": dur,
            "matrix_dimensions": f"{len(sources)}x{len(destinations)}",
            "finite_cells": finite_cells,
            "null_cells": null_cells,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "evidence_class": "DERIVED",
            "dq_status": "PASS",
        }
        
        manifest_path = os.path.join(MANIFESTS_DIR, "osrm_smoke_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

if __name__ == "__main__":
    test_osrm_smoke_server()
