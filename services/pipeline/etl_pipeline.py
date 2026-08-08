import os
import json
import hashlib
from datetime import datetime

ZONEPILOT_DATA_ROOT = os.environ.get('ZONEPILOT_DATA_ROOT', './data')

# Fixtures for Operational Data
MOCK_OPERATIONAL_DATA = [
    {"id": 1, "trip_id": "T001", "eta": 15, "zone": "Z1", "status": "active", "timestamp": "2026-08-07T10:00:00Z"},
    {"id": 2, "trip_id": "T001", "eta": 12, "zone": "Z1", "status": "active", "timestamp": "2026-08-07T10:05:00Z"},
    {"id": 3, "trip_id": "T001", "eta": 12, "zone": "Z1", "status": "active", "timestamp": "2026-08-07T10:05:00Z"}, # Duplicate
    {"id": 4, "trip_id": "T002", "eta": -5, "zone": "Z2", "status": "active", "timestamp": "2026-08-07T10:10:00Z"}, # Invalid ETA
    {"id": 5, "trip_id": "T003", "eta": 20, "zone": "Z3", "status": "inactive", "timestamp": "2026-08-07T10:15:00Z"}
]

MOCK_WEATHER = {
    "Z1": "Sunny",
    "Z2": "Rain",
    "Z3": "Cloudy"
}

ZONE_MAPPING = {
    "Z1": "North Zone",
    "Z2": "South Zone",
    "Z3": "East Zone"
}

def hash_row(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()

def step_snapshot():
    raw_dir = os.path.join(ZONEPILOT_DATA_ROOT, 'private', 'raw')
    os.makedirs(raw_dir, exist_ok=True)
    
    snapshot_data = {
        "manifest": {
            "schema": {"id": "int", "trip_id": "str", "eta": "int", "zone": "str", "status": "str", "timestamp": "str"},
            "row_count": len(MOCK_OPERATIONAL_DATA),
            "hashes": [hash_row(r) for r in MOCK_OPERATIONAL_DATA]
        },
        "rows": MOCK_OPERATIONAL_DATA
    }
    
    snapshot_path = os.path.join(raw_dir, f"snapshot_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json")
    with open(snapshot_path, 'w') as f:
        json.dump(snapshot_data, f, indent=2)
    return snapshot_path

def step_bronze(snapshot_path):
    bronze_dir = os.path.join(ZONEPILOT_DATA_ROOT, 'bronze')
    os.makedirs(bronze_dir, exist_ok=True)
    
    with open(snapshot_path, 'r') as f:
        data = json.load(f)
    
    # dedupe, parse, provenance
    seen_hashes = set()
    bronze_rows = []
    
    for row in data['rows']:
        h = hash_row(row)
        if h not in seen_hashes:
            seen_hashes.add(h)
            
            # parsing/types
            bronze_row = {
                "id": int(row["id"]),
                "trip_id": str(row["trip_id"]),
                "eta": int(row["eta"]),
                "zone": str(row["zone"]),
                "status": str(row["status"]),
                "timestamp": row["timestamp"], # keeping iso string
                "_provenance": {
                    "_source": "snapshot",
                    "_loaded_at": datetime.utcnow().isoformat()
                }
            }
            bronze_rows.append(bronze_row)
            
    bronze_path = os.path.join(bronze_dir, 'bronze_data.json')
    with open(bronze_path, 'w') as f:
        json.dump(bronze_rows, f, indent=2)
    return bronze_path

def step_silver(bronze_path):
    silver_dir = os.path.join(ZONEPILOT_DATA_ROOT, 'silver')
    os.makedirs(silver_dir, exist_ok=True)
    
    with open(bronze_path, 'r') as f:
        bronze_rows = json.load(f)
        
    silver_rows = []
    for row in bronze_rows:
        # canonical vocabulary
        canonical_status = row['status'].upper()
        # zone mapping
        mapped_zone = ZONE_MAPPING.get(row['zone'], "Unknown")
        # weather join
        weather = MOCK_WEATHER.get(row['zone'], "Unknown")
        
        silver_row = row.copy()
        silver_row['status'] = canonical_status
        silver_row['zone_name'] = mapped_zone
        silver_row['weather'] = weather
        
        silver_rows.append(silver_row)
        
    silver_path = os.path.join(silver_dir, 'silver_data.json')
    with open(silver_path, 'w') as f:
        json.dump(silver_rows, f, indent=2)
    return silver_path

def step_dq(silver_path):
    dq_dir = os.path.join(ZONEPILOT_DATA_ROOT, 'dq')
    os.makedirs(dq_dir, exist_ok=True)
    
    with open(silver_path, 'r') as f:
        silver_rows = json.load(f)
        
    report = {
        "completeness": 0,
        "invalid_eta_count": 0,
        "missing_intervals": 0,
        "failed_rows": []
    }
    
    valid_count = 0
    for row in silver_rows:
        is_valid = True
        if row['eta'] < 0:
            report['invalid_eta_count'] += 1
            is_valid = False
            report['failed_rows'].append({"id": row['id'], "reason": "Negative ETA"})
            
        if not row['timestamp']:
            report['missing_intervals'] += 1
            is_valid = False
            
        if is_valid:
            valid_count += 1
            
    report['completeness'] = (valid_count / len(silver_rows)) * 100 if silver_rows else 100
    
    report_path = os.path.join(dq_dir, 'dq_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    return report_path

if __name__ == "__main__":
    print("Starting Pipeline...")
    snap = step_snapshot()
    print(f"Snapshot created: {snap}")
    br = step_bronze(snap)
    print(f"Bronze layer created: {br}")
    si = step_silver(br)
    print(f"Silver layer created: {si}")
    dq = step_dq(si)
    print(f"DQ Report created: {dq}")
    print("Pipeline executed successfully.")
