import hashlib
import json
import os
import subprocess
from datetime import datetime

DATA_ROOT = os.environ.get("ZONEPILOT_DATA_ROOT", os.path.join(os.getcwd(), "data_root"))
OSM_DIR = os.path.join(DATA_ROOT, "private", "official", "raw", "osm")
GEOFABRIK_URL = "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def run_osm_midnight():
    """
    Downloads the official Geofabrik PBF for the Southern Zone of India,
    verifies checksum, and clips it to the Bengaluru pilot area using osmium.
    """
    print("Starting OSM Geofabrik Pipeline...")
    ensure_dir(OSM_DIR)
    
    pbf_path = os.path.join(OSM_DIR, "southern-zone-latest.osm.pbf")
    md5_path = os.path.join(OSM_DIR, "southern-zone-latest.osm.pbf.md5")
    
    # Download PBF and MD5
    print(f"Downloading {GEOFABRIK_URL}...")
    subprocess.run(["curl", "-s", "-o", pbf_path, GEOFABRIK_URL], check=True)
    subprocess.run(["curl", "-s", "-o", md5_path, GEOFABRIK_URL + ".md5"], check=True)
    
    # Verify MD5
    with open(md5_path, "r") as f:
        expected_md5 = f.read().split()[0]
        
    with open(pbf_path, "rb") as f:
        file_hash = hashlib.md5()
        chunk = f.read(8192)
        while chunk:
            file_hash.update(chunk)
            chunk = f.read(8192)
    actual_md5 = file_hash.hexdigest()
    
    if expected_md5 != actual_md5:
        raise ValueError(f"MD5 mismatch! Expected {expected_md5}, got {actual_md5}")
        
    print(f"PBF Checksum Verified: {actual_md5}")
    
    # Pilot Corridor Bounding Box (HSR, Koramangala, Indiranagar approximate)
    # BBOX: left,bottom,right,top
    BBOX = "77.58,12.90,77.65,12.98"
    pilot_pbf_path = os.path.join(OSM_DIR, "pilot_corridor.osm.pbf")
    
    print(f"Clipping to Pilot BBOX ({BBOX}) using osmium...")
    try:
        # Assuming osmium is installed in the runner environment
        subprocess.run([
            "osmium", "extract", "-b", BBOX, pbf_path, "-o", pilot_pbf_path, "--overwrite"
        ], check=True)
        print("Pilot clip successful.")
    except FileNotFoundError:
        print("osmium-tool not found on PATH. Please install osmium-tool (apt-get install osmium-tool).")
        raise
        
    # Extract Roads (highways)
    roads_pbf_path = os.path.join(OSM_DIR, "pilot_roads.osm.pbf")
    print("Extracting road network...")
    subprocess.run([
        "osmium", "tags-filter", pilot_pbf_path, "w/highway", "-o", roads_pbf_path, "--overwrite"
    ], check=True)
    
    # Extract POIs (amenities, shops)
    pois_pbf_path = os.path.join(OSM_DIR, "pilot_pois.osm.pbf")
    print("Extracting POIs...")
    subprocess.run([
        "osmium", "tags-filter", pilot_pbf_path, "n/amenity", "n/shop", "-o", pois_pbf_path, "--overwrite"
    ], check=True)
    
    # Write Manifest
    manifest = {
        "provider": "osm_geofabrik",
        "dataset": "pilot_network_extract",
        "timestamp": datetime.now().isoformat(),
        "source_pbf": GEOFABRIK_URL,
        "source_md5": actual_md5,
        "bbox": BBOX
    }
    with open(os.path.join(OSM_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    run_osm_midnight()
