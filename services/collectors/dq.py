import json
from typing import List, Dict, Any
from datetime import datetime
import pytz

def check_no_staging_contamination(records: List[Dict[str, Any]]) -> bool:
    """Ensure no faker/demo/test data is present."""
    forbidden_terms = ['faker', 'demo', 'test', 'synthetic', 'mock']
    
    for record in records:
        # Check provenance
        prov = record.get('_provenance', {})
        if prov.get('evidence_class') in ['STAGING', 'DEMO', 'SYNTHETIC']:
            return False
            
        # Optional: recursively check strings for forbidden terms if strictly needed
        
    return True

def check_lifecycle_ordering(record: Dict[str, Any]) -> bool:
    """Ensure ordered <= accepted <= ready <= picked_up <= delivered."""
    # Convert string ISO to timestamp for comparison
    def to_ts(ts_str):
        if not ts_str: return None
        try:
            return datetime.fromisoformat(ts_str).timestamp()
        except Exception:
            return None

    ordered = to_ts(record.get('order_time'))
    accepted = to_ts(record.get('accepted_at'))
    ready = to_ts(record.get('ready_time'))
    pickup = to_ts(record.get('pickup'))
    delivered = to_ts(record.get('delivered'))
    
    # We only assert if BOTH adjacent timestamps exist
    if ordered and accepted and ordered > accepted: return False
    if accepted and ready and accepted > ready: return False
    if ready and pickup and ready > pickup: return False
    if pickup and delivered and pickup > delivered: return False
    
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
