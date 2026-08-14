import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

import httpx
import pytz
import yaml

from services.collectors.db import (
    init_db,
    record_run_complete,
    record_run_error,
    record_run_start,
)
from services.collectors.storage import ensure_directories, save_bronze_data, save_raw_data, save_silver_data


class TomTomClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('TOMTOM_API_KEY')
        self.base_url = "https://api.tomtom.com/traffic/services/4"
        self.routing_url = "https://api.tomtom.com/routing/1/calculateRoute"

    def check_auth(self):
        if not self.api_key:
            raise ValueError("TomTom API key missing. READY_NEEDS_API_KEY")

    def fetch_live_traffic_for_route(self, waypoints: List[str]) -> Dict[str, Any]:
        """Fetch routing travel time using TomTom Routing API which incorporates live traffic."""
        self.check_auth()
        # TomTom requires waypoints joined by colon: lat,lon:lat,lon
        locations = ":".join(waypoints)
        url = f"{self.routing_url}/{locations}/json"
        
        params = {
            "key": self.api_key,
            "computeTravelTimeFor": "all",
            "traffic": "true"
        }
        with httpx.Client() as client:
            res = client.get(url, params=params)
            res.raise_for_status()
            return res.json()

def load_pilot_routes() -> List[Dict[str, Any]]:
    # Assumes run from repo root
    config_path = os.path.join(os.getcwd(), 'configs', 'data', 'bengaluru_pilot_routes.yaml')
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)
        return data.get('pilot_corridor', {}).get('routes', [])

def process_tomtom_bronze(raw_data: Dict[str, Any], retrieved_at: str, run_id: str, route_id: str) -> List[Dict[str, Any]]:
    routes = raw_data.get('routes', [])
    if not routes:
        return []
    
    # We take the best route's summary
    summary = routes[0].get('summary', {})
    
    bronze_record = summary.copy()
    bronze_record['route_id'] = route_id
    bronze_record['_provenance'] = {
        "provider": "tomtom",
        "dataset": "live_traffic_route",
        "run_id": run_id,
        "retrieved_at": retrieved_at,
        "evidence_class": "PROVIDER_ESTIMATED"
    }
    return [bronze_record]

def process_tomtom_silver(bronze_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    silver = []
    for record in bronze_data:
        retrieved_at = datetime.fromisoformat(record['_provenance']['retrieved_at'])
        
        # Determine event time. TomTom routing is "now".
        silver_record = {
            "traffic_event_id": f"TT-RTE-{record['route_id']}-{uuid.uuid4()}",
            "route_id": record['route_id'],
            "event_time": retrieved_at.isoformat(),
            "information_available_at": retrieved_at.isoformat(),
            "current_travel_time_sec": record.get("travelTimeInSeconds"),
            "free_flow_travel_time_sec": record.get("noTrafficTravelTimeInSeconds"),
            "historical_travel_time_sec": record.get("historicTrafficTravelTimeInSeconds"),
            "delay_sec": record.get("trafficDelayInSeconds"),
            "length_meters": record.get("lengthInMeters"),
            "_provenance": record.get("_provenance")
        }
        silver.append(silver_record)
    return silver

def run_tomtom_intraday():
    init_db()
    ensure_directories()
    
    provider = "tomtom"
    dataset = "live_traffic_route"
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    
    try:
        client = TomTomClient()
        client.check_auth()
    except ValueError as e:
        print(str(e))
        return

    run_id = str(uuid.uuid4())
    logical_date = now.strftime('%Y-%m-%d')
    routes = load_pilot_routes()
    
    try:
        record_run_start(run_id, provider, dataset, "PROSPECTIVE_LIVE", logical_date)
        total_written = 0
        
        for route in routes:
            route_id = route['route_id']
            # Format waypoints: List of "lat,lon" strings
            waypoints = []
            for wp in route.get('waypoints', []):
                # We expect wp to be a list [lat, lon] or string "lat,lon"
                # From yaml it parsed as a string because it had a comma without quotes?
                # Wait, in YAML `- 12.9141, 77.6358` parses as a single string.
                waypoints.append(str(wp).replace(' ', ''))
                
            raw_data = client.fetch_live_traffic_for_route(waypoints)
            save_raw_data(provider, dataset, now, run_id, raw_data, f"raw_route_{route_id}.json")
            
            retrieved_at = now.isoformat()
            bronze_data = process_tomtom_bronze(raw_data, retrieved_at, run_id, route_id)
            save_bronze_data(provider, dataset, now, run_id, bronze_data, f"bronze_{route_id}.jsonl")
            
            silver_data = process_tomtom_silver(bronze_data)
            save_silver_data(provider, dataset, now, run_id, silver_data, f"silver_{route_id}.jsonl")
            total_written += len(silver_data)
            
        record_run_complete(run_id, total_written, total_written, None)
        print(f"[{run_id}] Success. Saved {total_written} TomTom routing records.")
        
    except Exception as e:
        print(f"[{run_id}] Failed intraday traffic: {str(e)}")
        record_run_error(run_id, "EXCEPTION")

def run_tomtom_midnight():
    # Placeholder for the Historical Traffic Stats job submission and download
    print("TomTom Historical Traffic backfill: READY_NEEDS_TRAFFIC_STATS_SUBSCRIPTION")

if __name__ == "__main__":
    run_tomtom_intraday()
