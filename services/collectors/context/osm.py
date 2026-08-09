import hashlib
import json
import os
import subprocess
from datetime import datetime

DATA_ROOT = os.environ.get("ZONEPILOT_DATA_ROOT", os.path.join(os.getcwd(), "data_root"))
OSM_DIR = os.path.join(DATA_ROOT, "private", "official", "raw", "osm")
GEOFABRIK_URL = "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"
OSMIUM_IMAGE = "stefda/osmium-tool@sha256:d2321d0e926f77ead7547b4b35f5cf98d9fd74043673cecc4fc2bb7cce06ff63"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def run_osmium(command_args):
    """Run osmium via docker"""
    # Fix paths for docker volume mount: mount OSM_DIR to /data
    cmd = [
        "docker", "run", "--rm", "-v", f"{OSM_DIR}:/data", OSMIUM_IMAGE, "osmium"
    ] + command_args
    subprocess.run(cmd, check=True)

def run_osm_midnight():
    """
    Downloads the official Geofabrik PBF for the Southern Zone of India,
    verifies checksum, and clips it to the Bengaluru pilot area using osmium.
    """
    print("Starting OSM Geofabrik Pipeline (Subagent 3)...")
    ensure_dir(OSM_DIR)
    
    pbf_path = os.path.join(OSM_DIR, "southern-zone-latest.osm.pbf")
    md5_path = os.path.join(OSM_DIR, "southern-zone-latest.osm.pbf.md5")
    
    # Download PBF and MD5
    print(f"Downloading {GEOFABRIK_URL}...")
    if not os.path.exists(pbf_path):
        subprocess.run(["curl", "-s", "-L", "-o", pbf_path, GEOFABRIK_URL], check=True)
    if not os.path.exists(md5_path):
        subprocess.run(["curl", "-s", "-L", "-o", md5_path, GEOFABRIK_URL + ".md5"], check=True)
    
    # Verify MD5
    with open(md5_path, "r") as f:
        expected_md5 = f.read().split()[0]
        
    print("Hashing PBF...")
    file_hash = hashlib.md5()
    with open(pbf_path, "rb") as f:
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
    actual_md5 = file_hash.hexdigest()
    
    if expected_md5 != actual_md5:
        print(f"MD5 mismatch! Expected {expected_md5}, got {actual_md5}")
        print("INTEGRITY_FAILED")
        import sys
        sys.exit(1)
    else:
        print(f"PBF Checksum Verified: {actual_md5}")
    
    # Pilot Corridor Bounding Box (HSR, Koramangala, Indiranagar approx)
    BBOX = "77.58,12.90,77.65,12.98"
    pilot_pbf_name = "pilot_corridor.osm.pbf"
    pilot_pbf_path = os.path.join(OSM_DIR, pilot_pbf_name)
    
    print(f"Clipping to Pilot BBOX ({BBOX}) using osmium...")
    run_osmium(["extract", "-b", BBOX, "/data/southern-zone-latest.osm.pbf", "-o", f"/data/{pilot_pbf_name}", "--overwrite"])
    print("Pilot clip successful.")
    
    # Extract Roads (highways)
    roads_pbf_name = "pilot_roads.osm.pbf"
    print("Extracting road network...")
    run_osmium(["tags-filter", f"/data/{pilot_pbf_name}", "w/highway", "-o", f"/data/{roads_pbf_name}", "--overwrite"])
    
    # Extract POIs (amenities, shops, crafts)
    pois_pbf_name = "pilot_pois.osm.pbf"
    print("Extracting POIs...")
    run_osmium(["tags-filter", f"/data/{pilot_pbf_name}", "n/amenity", "n/shop", "n/craft", "-o", f"/data/{pois_pbf_name}", "--overwrite"])
    
    # Export POIs to GeoJSON
    silver_pois_name = "silver_pois.geojson"
    print("Exporting POIs to GeoJSON...")
    run_osmium(["export", f"/data/{pois_pbf_name}", "-o", f"/data/{silver_pois_name}", "--overwrite"])
    
    # Run osmium fileinfo to get node and edge counts
    print("Getting road graph statistics...")
    info_proc = subprocess.run([
        "docker", "run", "--rm", "-v", f"{OSM_DIR}:/data", OSMIUM_IMAGE,
        "osmium", "fileinfo", "-e", f"/data/{roads_pbf_name}"
    ], capture_output=True, text=True, check=True)
    
    nodes_count = 0
    ways_count = 0
    for line in info_proc.stdout.splitlines():
        if "Number of nodes:" in line:
            nodes_count = int(line.split()[-1])
        if "Number of ways:" in line:
            ways_count = int(line.split()[-1])
            
    print("Getting POI statistics...")
    poi_info_proc = subprocess.run([
        "docker", "run", "--rm", "-v", f"{OSM_DIR}:/data", OSMIUM_IMAGE,
        "osmium", "fileinfo", "-e", f"/data/{pois_pbf_name}"
    ], capture_output=True, text=True, check=True)
    
    pois_count = 0
    for line in poi_info_proc.stdout.splitlines():
        if "Number of nodes:" in line:
            pois_count = int(line.split()[-1])
            
    # Write Manifest
    manifest = {
        "provider": "osm_geofabrik",
        "dataset": "pilot_network_extract",
        "timestamp": datetime.now().isoformat(),
        "source_pbf": GEOFABRIK_URL,
        "source_md5": actual_md5,
        "bbox": BBOX,
        "clip_size_bytes": os.path.getsize(pilot_pbf_path),
        "osm_pbf_nodes": nodes_count,
        "osm_highway_ways": ways_count,
        "pois": pois_count
    }
    with open(os.path.join(OSM_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
        
    print("OSM Pipeline Executed Successfully:")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    run_osm_midnight()
