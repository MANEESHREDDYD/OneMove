import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from services.evidence.r1 import candidate_code_sha, sha256_file, sha256_file_set

OSRM_IMAGE = "osrm/osrm-backend@sha256:af5d4a83fb90086a43b1ae2ca22872e6768766ad5fcbb07a29ff90ec644ee409"
DATA_ROOT = os.environ.get("ZONEPILOT_DATA_ROOT", os.path.join(os.getcwd(), "data_root"))
OSM_DIR = os.path.join(DATA_ROOT, "private", "official", "raw", "osm")
OSRM_DIR = os.path.join(DATA_ROOT, "private", "official", "raw", "osrm")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def measure_time(step_name, func, *args, **kwargs):
    """Utility to measure and print execution time of a step."""
    start = time.time()
    print(f"[{datetime.now().isoformat()}] Starting: {step_name}")
    result = func(*args, **kwargs)
    duration = time.time() - start
    print(f"[{datetime.now().isoformat()}] Finished: {step_name} in {duration:.2f} seconds")
    return duration, result

def run_docker_osrm(command, *args):
    """Run an OSRM command via Docker, mounting the OSRM_DIR."""
    docker_args = ["docker", "run", "-t"]
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        # Keep generated graph files readable by the CI runner. Without this,
        # the container can emit root-owned files with owner-only permissions.
        docker_args.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
    docker_args.extend(["-v", f"{OSRM_DIR}:/data", OSRM_IMAGE, command])
    subprocess.run(docker_args + list(args), check=True)

def build_osrm_graph():
    ensure_dir(OSRM_DIR)
    
    # Copy pilot_roads.osm.pbf to OSRM dir for processing
    pbf_source = os.path.join(OSM_DIR, "pilot_roads.osm.pbf")
    pbf_target = os.path.join(OSRM_DIR, "pilot_roads.osm.pbf")
    
    if not os.path.exists(pbf_source):
        raise FileNotFoundError(f"Source PBF not found: {pbf_source}")
        
    shutil.copy(pbf_source, pbf_target)
    
    # 1. Extract
    extract_time, _ = measure_time(
        "OSRM Extract", 
        run_docker_osrm, "osrm-extract", "-p", "/opt/car.lua", "/data/pilot_roads.osm.pbf"
    )
    
    # 2. Partition
    partition_time, _ = measure_time(
        "OSRM Partition", 
        run_docker_osrm, "osrm-partition", "/data/pilot_roads.osrm"
    )
    
    # 3. Customize
    customize_time, _ = measure_time(
        "OSRM Customize", 
        run_docker_osrm, "osrm-customize", "/data/pilot_roads.osrm"
    )
    
    # Save Benchmark
    generated_at = datetime.now(timezone.utc).isoformat()
    graph_files = [path for path in Path(OSRM_DIR).glob("pilot_roads.osrm*") if path.is_file()]
    benchmark = {
        "schema_name": "zonepilot_osrm_build_manifest",
        "schema_version": "1.0.0",
        "timestamp": generated_at,
        "generated_at": generated_at,
        "image": OSRM_IMAGE,
        "extract_time_seconds": extract_time,
        "partition_time_seconds": partition_time,
        "customize_time_seconds": customize_time,
        "total_time_seconds": extract_time + partition_time + customize_time,
        "graph_file_count": len(graph_files),
        "graph_size_bytes": sum(path.stat().st_size for path in graph_files),
        "input_pbf_sha256": sha256_file(Path(pbf_target)),
        "graph_bundle_sha256": sha256_file_set(graph_files, relative_to=Path(OSRM_DIR)),
        "code_sha": candidate_code_sha(),
        "evidence_class": "DERIVED",
        "dq_status": "PASS",
    }
    
    with open(os.path.join(OSRM_DIR, "benchmark.json"), "w") as f:
        json.dump(benchmark, f, indent=2)
        
    print(f"OSRM Benchmark Complete: {benchmark}")
    return benchmark

if __name__ == "__main__":
    build_osrm_graph()
