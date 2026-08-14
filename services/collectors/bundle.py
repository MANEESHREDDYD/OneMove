import datetime
import hashlib
import json
import os

from services.evidence.r1 import candidate_code_sha

DATA_ROOT = os.environ.get("ZONEPILOT_DATA_ROOT", os.path.join(os.getcwd(), "data_root"))
PRIVATE_DIR = os.path.join(DATA_ROOT, "private", "official")
CHECKPOINTS_DIR = os.path.join(PRIVATE_DIR, "checkpoints")

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def build_daily_bundle():
    ensure_dir(CHECKPOINTS_DIR)
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    bundle_path = os.path.join(CHECKPOINTS_DIR, f"{today}_bundle.json")
    
    bundle = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "date": today,
        "components": {}
    }
    
    # OSM Manifest
    osm_manifest = os.path.join(PRIVATE_DIR, "raw", "osm", "manifest.json")
    if os.path.exists(osm_manifest):
        with open(osm_manifest, "r") as f:
            bundle["components"]["osm"] = json.load(f)
            
    # OSRM Benchmark
    osrm_bench = os.path.join(PRIVATE_DIR, "raw", "osrm", "benchmark.json")
    if os.path.exists(osrm_bench):
        with open(osrm_bench, "r") as f:
            bundle["components"]["osrm"] = json.load(f)
            
    # OpenMeteo Manifest (if it exists)
    openmeteo_manifest = os.path.join(PRIVATE_DIR, "raw", "weather", "openmeteo", "manifest.json")
    if os.path.exists(openmeteo_manifest):
        with open(openmeteo_manifest, "r") as f:
            bundle["components"]["openmeteo"] = json.load(f)
            
    # TomTom Status (if it exists)
    tomtom_manifest = os.path.join(PRIVATE_DIR, "raw", "traffic", "tomtom", "manifest.json")
    if os.path.exists(tomtom_manifest):
        with open(tomtom_manifest, "r") as f:
            bundle["components"]["tomtom"] = json.load(f)
            
    # Calculate intervals (for a 15-minute interval system, expected is 96 per day)
    expected = 96
    available = expected if "tomtom" in bundle["components"] else 0
    missing = expected - available
    
    # Bundle Hash
    bundle_str = json.dumps(bundle, sort_keys=True)
    bundle_hash = hashlib.sha256(bundle_str.encode('utf-8')).hexdigest()
    
    with open(bundle_path, "w") as f:
        f.write(bundle_str)
        
    print(f"Built daily bundle at {bundle_path}")
    
    # 2. Build Small Public Manifest
    public_manifest_dir = os.path.join(DATA_ROOT, "public", "manifests")
    ensure_dir(public_manifest_dir)
    
    source_hashes = {}
    for k, v in bundle["components"].items():
        source_hashes[k] = hashlib.sha256(json.dumps(v, sort_keys=True).encode('utf-8')).hexdigest()
        
    manifest = {
        "logical_date": today,
        "included_provider_partitions": list(bundle["components"].keys()),
        "expected_intervals": expected,
        "available_intervals": available,
        "missing_intervals": missing,
        "source_manifest_hashes": source_hashes,
        "output_bundle_hash": bundle_hash,
        "code_sha": candidate_code_sha(),
        "schema_version": "1.0.0",
        "evidence_class": "PUBLIC_OFFICIAL",
    }
    
    manifest_path = os.path.join(public_manifest_dir, f"{today}_bundle_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Built public bundle manifest at {manifest_path}")
    print(json.dumps(manifest, indent=2))
    return manifest

if __name__ == "__main__":
    build_daily_bundle()
