import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytz

from services.collectors.db import (
    get_provider_state,
    init_db,
    record_run_complete,
    record_run_error,
    record_run_start,
    set_provider_state,
)
from services.collectors.platforms.swiggy.mcp_client import SwiggyAuthenticator, SwiggyMCPClient
from services.collectors.storage import ensure_directories, save_bronze_data, save_raw_data, save_silver_data


def process_swiggy_bronze(raw_data: Dict[str, Any], retrieved_at: str, run_id: str) -> List[Dict[str, Any]]:
    orders = raw_data.get('orders', [])
    bronze = []
    for order in orders:
        bronze_record = order.copy()
        bronze_record['_provenance'] = {
            "provider": "swiggy",
            "dataset": "food",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "evidence_class": "OFFICIAL_API_REAL"
        }
        bronze.append(bronze_record)
    return bronze

def process_swiggy_silver(bronze_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    silver = []
    for record in bronze_data:
        # Construct the canonical schema as requested
        silver_record = {
            "platform": "Swiggy Food",
            "order_id_hash": record.get("order_id"), # Assume already pseudonymized or hash it if needed
            "merchant_id_hash": record.get("restaurant", {}).get("id"),
            "items_ordered": [item.get("name") for item in record.get("order_items", [])] if record.get("order_items") else None,
            "order_total": record.get("billing", {}).get("total_amount"),
            "delivery_fee": record.get("billing", {}).get("delivery_fee"),
            "order_time": record.get("created_at"),
            "provider_eta": record.get("promised_delivery_time"),
            "accepted_at": record.get("status_timestamps", {}).get("accepted"),
            "ready_time": record.get("status_timestamps", {}).get("food_ready"),
            "rider_assigned": record.get("status_timestamps", {}).get("delivery_partner_assigned"),
            "pickup": record.get("status_timestamps", {}).get("picked_up"),
            "delivered": record.get("status_timestamps", {}).get("delivered"),
            "cancelled": record.get("status_timestamps", {}).get("cancelled"),
            "rider_id_hash": record.get("delivery_partner", {}).get("id"),
            "_provenance": record.get("_provenance")
        }
        silver.append(silver_record)
    return silver

def run_swiggy_food_collection():
    init_db()
    ensure_directories()
    
    provider = "swiggy"
    dataset = "food"
    
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    
    try:
        auth = SwiggyAuthenticator()
        client = SwiggyMCPClient(auth)
    except ValueError as e:
        print(str(e))
        return

    # Check last fetched state
    last_fetched = get_provider_state(provider, dataset, "last_fetched_date")
    
    if not last_fetched:
        start_date = (now - timedelta(days=90)).strftime('%Y-%m-%d')
        mode = "HISTORICAL_BACKFILL"
    else:
        last_dt = datetime.strptime(last_fetched, '%Y-%m-%d').date()
        start_date = (last_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        mode = "PROSPECTIVE_LIVE"
        
    end_date = now.strftime('%Y-%m-%d') 
    
    if start_date > end_date:
        print("Swiggy Food: Already up to date.")
        return

    run_id = str(uuid.uuid4())
    logical_date = start_date 
    
    try:
        record_run_start(run_id, provider, dataset, mode, logical_date)
        print(f"[{run_id}] Fetching Swiggy Food {mode} since {start_date}...")
        
        raw_data = client.fetch_food_orders(since=start_date)
        
        raw_hash = save_raw_data(provider, dataset, now, run_id, raw_data, "raw_response.json")
        
        retrieved_at = now.isoformat()
        bronze_data = process_swiggy_bronze(raw_data, retrieved_at, run_id)
        save_bronze_data(provider, dataset, now, run_id, bronze_data, "bronze_events.jsonl")
        
        silver_data = process_swiggy_silver(bronze_data)
        save_silver_data(provider, dataset, now, run_id, silver_data, "silver_events.jsonl")
        
        records_written = len(silver_data)
        record_run_complete(run_id, records_written, records_written, raw_hash)
        
        set_provider_state(provider, dataset, "last_fetched_date", end_date)
        print(f"[{run_id}] Success. Saved {records_written} records.")
        
    except Exception as e:
        print(f"[{run_id}] Failed: {str(e)}")
        record_run_error(run_id, "EXCEPTION")

if __name__ == "__main__":
    run_swiggy_food_collection()
