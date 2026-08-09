import json
import os
import subprocess
import time
from datetime import datetime

# Pin OSRM image to an explicit version/digest as per mandate
OSRM_IMAGE = "osrm/osrm-backend:v5.27.1"
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
    subprocess.run([
        "docker", "run", "-t", "-v", f"{OSRM_DIR}:/data", OSRM_IMAGE, command
    ] + list(args), check=True)

def build_osrm_graph():
    ensure_dir(OSRM_DIR)
    
    # Copy pilot_roads.osm.pbf to OSRM dir for processing
    pbf_source = os.path.join(OSM_DIR, "pilot_roads.osm.pbf")
    pbf_target = os.path.join(OSRM_DIR, "pilot_roads.osm.pbf")
    
    if not os.path.exists(pbf_source):
        print(f"Source PBF not found: {pbf_source}")
        return
        
    subprocess.run(["cp", pbf_source, pbf_target], check=True)
    
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
    benchmark = {
        "timestamp": datetime.now().isoformat(),
        "image": OSRM_IMAGE,
        "extract_time_seconds": extract_time,
        "partition_time_seconds": partition_time,
        "customize_time_seconds": customize_time,
        "total_time_seconds": extract_time + partition_time + customize_time,
        "graph_size_bytes": os.path.getsize(os.path.join(OSRM_DIR, "pilot_roads.osrm"))
    }
    
    with open(os.path.join(OSRM_DIR, "benchmark.json"), "w") as f:
        json.dump(benchmark, f, indent=2)
        
    print(f"OSRM Benchmark Complete: {benchmark}")

if __name__ == "__main__":
    build_osrm_graph()
