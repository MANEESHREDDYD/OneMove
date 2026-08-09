import os
import uuid
from datetime import datetime
from typing import Any, Dict, List

import pytz

from services.collectors.db import (
    init_db,
    record_run_complete,
    record_run_error,
    record_run_start,
)
from services.collectors.storage import ensure_directories, save_bronze_data, save_raw_data, save_silver_data


class ZomatoPOSClient:
    def __init__(self, partner_key: str = None):
        self.partner_key = partner_key or os.environ.get('ZOMATO_PARTNER_KEY')

    def check_auth(self):
        if not self.partner_key:
            raise ValueError("Zomato POS credentials missing. READY_NEEDS_OFFICIAL_ZOMATO_ACCESS")

    def fetch_historical_orders(self, since: str) -> Dict[str, Any]:
        """Fetch historical orders if the POS API supports it."""
        self.check_auth()
        # To be implemented when official documentation is available for POS integrations
        return {"orders": []}

    def fetch_active_orders(self) -> Dict[str, Any]:
        """Fetch active/live orders if the POS API supports it."""
        self.check_auth()
        # To be implemented
        return {"orders": []}

def process_zomato_bronze(raw_data: Dict[str, Any], retrieved_at: str, run_id: str) -> List[Dict[str, Any]]:
    orders = raw_data.get('orders', [])
    bronze = []
    for order in orders:
        bronze_record = order.copy()
        bronze_record['_provenance'] = {
            "provider": "zomato",
            "dataset": "pos_orders",
            "run_id": run_id,
            "retrieved_at": retrieved_at,
            "evidence_class": "OFFICIAL_API_REAL"
        }
        bronze.append(bronze_record)
    return bronze

def process_zomato_silver(bronze_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    silver = []
    for record in bronze_data:
        # Construct the canonical schema as requested
        silver_record = {
            "platform": "Zomato",
            "order_id_hash": record.get("order_id"), 
            "merchant_id_hash": record.get("restaurant_id"),
            "items_ordered": [item.get("name") for item in record.get("items", [])] if record.get("items") else None,
            "order_total": record.get("total_price"),
            "delivery_fee": record.get("delivery_fee"),
            "order_time": record.get("order_time"),
            # Many fields might be NOT_EXPOSED as per documentation limits
            "provider_eta": None,
            "accepted_at": record.get("accepted_time"),
            "ready_time": record.get("ready_time"),
            "rider_assigned": record.get("rider_assigned_time"),
            "pickup": record.get("pickup_time"),
            "delivered": record.get("delivery_time"),
            "cancelled": record.get("cancelled_time"),
            "rider_id_hash": record.get("rider_id"),
            "_provenance": record.get("_provenance")
        }
        silver.append(silver_record)
    return silver

def run_zomato_pos_collection():
    init_db()
    ensure_directories()
    
    provider = "zomato"
    dataset = "pos_orders"
    
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)
    
    try:
        client = ZomatoPOSClient()
        client.check_auth()
    except ValueError as e:
        print(str(e))
        return

    # If auth was provided, continue...
    run_id = str(uuid.uuid4())
    logical_date = now.strftime('%Y-%m-%d')
    
    try:
        record_run_start(run_id, provider, dataset, "PROSPECTIVE_LIVE", logical_date)
        
        raw_data = client.fetch_active_orders()
        raw_hash = save_raw_data(provider, dataset, now, run_id, raw_data, "raw_response.json")
        
        retrieved_at = now.isoformat()
        bronze_data = process_zomato_bronze(raw_data, retrieved_at, run_id)
        save_bronze_data(provider, dataset, now, run_id, bronze_data, "bronze_events.jsonl")
        
        silver_data = process_zomato_silver(bronze_data)
        save_silver_data(provider, dataset, now, run_id, silver_data, "silver_events.jsonl")
        
        records_written = len(silver_data)
        record_run_complete(run_id, records_written, records_written, raw_hash)
        print(f"[{run_id}] Success. Saved {records_written} Zomato records.")
        
    except Exception as e:
        print(f"[{run_id}] Failed: {str(e)}")
        record_run_error(run_id, "EXCEPTION")

if __name__ == "__main__":
    run_zomato_pos_collection()
