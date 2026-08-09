import json
import os
import subprocess
import time
import httpx
import pytest
import math

OSRM_IMAGE = "osrm/osrm-backend@sha256:af5d4a83fb90086a43b1ae2ca22872e6768766ad5fcbb07a29ff90ec644ee409"
DATA_ROOT = os.environ.get("ZONEPILOT_DATA_ROOT", os.path.join(os.getcwd(), "data_root"))
OSRM_DIR = os.path.join(DATA_ROOT, "private", "official", "raw", "osrm")

def test_osrm_smoke_server():
    if not os.path.exists(os.path.join(OSRM_DIR, "pilot_roads.osrm")):
        print("Graph not built! Please run osrm_pipeline.py first.")
        return
        
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
        time.sleep(3)
        client = httpx.Client()
        
        # 1. Route Request
        origin = "77.63,12.91"
        dest = "77.64,12.92"
        route_url = f"http://localhost:5000/route/v1/driving/{origin};{dest}?overview=false"
        
        res_route = client.get(route_url, timeout=5.0)
        route_status = res_route.status_code
        route_data = res_route.json() if route_status == 200 else {}
        
        dist = route_data.get("routes", [{}])[0].get("distance", -1)
        dur = route_data.get("routes", [{}])[0].get("duration", -1)
        
        print("\n=== OSRM ROUTE EVIDENCE ===")
        print(f"Origin: {origin}")
        print(f"Destination: {dest}")
        print(f"HTTP Status: {route_status}")
        print(f"Distance (m): {dist}")
        print(f"Duration (s): {dur}")
        print(f"Finite values: {math.isfinite(dist) and math.isfinite(dur) and dist > 0}")

        # 2. Table Request
        coords = "77.63,12.91;77.64,12.92;77.62,12.90"
        table_url = f"http://localhost:5000/table/v1/driving/{coords}"
        
        res_table = client.get(table_url, timeout=5.0)
        table_status = res_table.status_code
        table_data = res_table.json() if table_status == 200 else {}
        
        sources = table_data.get("sources", [])
        destinations = table_data.get("destinations", [])
        durations = table_data.get("durations", [])
        
        num_sources = len(sources)
        num_destinations = len(destinations)
        
        finite_cells = 0
        null_cells = 0
        
        for row in durations:
            for cell in row:
                if cell is None:
                    null_cells += 1
                elif math.isfinite(cell):
                    finite_cells += 1
                    
        print("\n=== OSRM TABLE EVIDENCE ===")
        print(f"Source count: {num_sources}")
        print(f"Destination count: {num_destinations}")
        print(f"Matrix dimensions: {num_sources}x{num_destinations}")
        print(f"Finite cells: {finite_cells}")
        print(f"Null/unreachable cells: {null_cells}")
        
    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

if __name__ == "__main__":
    test_osrm_smoke_server()
