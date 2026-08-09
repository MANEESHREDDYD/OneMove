import httpx
import os
from datetime import datetime
import pytz
import uuid
from typing import Dict, Any, List

from services.collectors.db import init_db, record_run_start, record_run_complete, record_run_error, get_provider_state, set_provider_state
from services.collectors.storage import ensure_directories, save_raw_data

def get_geofabrik_state() -> str:
    # URL for Southern Zone India
    url = "https://download.geofabrik.de/asia/india/southern-zone-updates/state.txt"
    try:
        with httpx.Client() as client:
            res = client.get(url)
            res.raise_for_status()
            # Extract sequence number
            for line in res.text.split('\n'):
                if line.startswith('sequenceNumber='):
                    return line.split('=')[1].strip()
    except Exception as e:
        print(f"Warning: Could not check Geofabrik state: {e}")
        return "UNKNOWN"

def run_osm_midnight():
    init_db()
    ensure_directories()
    
    provider = "osm"
    dataset = "southern_zone_india"
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    
    run_id = str(uuid.uuid4())
    logical_date = now.strftime('%Y-%m-%d')
    
    try:
        current_sequence = get_geofabrik_state()
        last_sequence = get_provider_state(provider, dataset, "last_sequence_number")
        
        if current_sequence != "UNKNOWN" and current_sequence == last_sequence:
            print("OSM/Geofabrik: Up to date. No upstream change.")
            return
            
        record_run_start(run_id, provider, dataset, "INCREMENTAL_UPDATE", logical_date)
        
        # We would download the PBF and clip it here, then generate OSRM graphs.
        # This is a heavily IO/Compute bound process, we simulate the metadata save for the ledger.
        metadata = {
            "upstream_sequence": current_sequence,
            "region": "southern-zone-india",
            "checked_at": now.isoformat(),
            "status": "DOWNLOAD_SIMULATED_FOR_NOW"
        }
        
        raw_hash = save_raw_data(provider, dataset, now, run_id, metadata, "osm_metadata.json")
        
        set_provider_state(provider, dataset, "last_sequence_number", current_sequence)
        record_run_complete(run_id, 0, 0, raw_hash)
        print(f"[{run_id}] OSM state updated to sequence {current_sequence}.")
        
    except Exception as e:
        print(f"[{run_id}] Failed OSM update: {str(e)}")
        record_run_error(run_id, "EXCEPTION")

if __name__ == "__main__":
    run_osm_midnight()
