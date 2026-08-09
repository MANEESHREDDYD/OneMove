import json
from datetime import datetime
from typing import Any, Dict, List


def check_no_staging_contamination(records: List[Dict[str, Any]]) -> bool:
    """Ensure no faker/demo/test data is present."""
    forbidden_terms = ['faker', 'demo', 'test', 'synthetic', 'mock']
    
    for record in records:
        text = json.dumps(record).lower()
        for term in forbidden_terms:
            if term in text:
                return False
            
    return True

def check_lifecycle_ordering(record: Dict[str, Any]) -> bool:
    """Ensure ordered <= accepted <= ready <= picked_up <= delivered."""
    # Convert string ISO to timestamp for comparison
    def to_ts(ts_str):
        if not ts_str: 
            return None
        try:
            return datetime.fromisoformat(ts_str).timestamp()
        except Exception:
            return None

    ordered = to_ts(record.get('ordered_at'))
    accepted = to_ts(record.get('accepted_at'))
    ready = to_ts(record.get('ready_at'))
    pickup = to_ts(record.get('pickup_at'))
    delivered = to_ts(record.get('delivered_at'))
    
    # We only assert if BOTH adjacent timestamps exist
    if ordered and accepted and ordered > accepted: 
        return False
    if accepted and ready and accepted > ready: 
        return False
    if ready and pickup and ready > pickup: 
        return False
    if pickup and delivered and pickup > delivered: 
        return False
    
    return True

def run_dq_checks(silver_records: List[Dict[str, Any]]) -> bool:
    if not check_no_staging_contamination(silver_records):
        print("DQ FAILED: Staging/Synthetic data detected in official records.")
        return False
        
    for r in silver_records:
        if not check_lifecycle_ordering(r):
            print(f"DQ FAILED: Lifecycle ordering violation in record {r.get('order_id_hash', 'Unknown')}.")
            return False
            
    return True
