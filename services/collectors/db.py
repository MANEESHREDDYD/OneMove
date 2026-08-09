import os
import json
from datetime import datetime
import pytz

def get_ledger_path():
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    path = os.path.join(repo_root, "data", "rolling", "dataset_registry.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def _load_ledger():
    path = get_ledger_path()
    if os.path.exists(path):
        with open(path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                pass
    return {"provider_state": {}, "runs": {}}

def _save_ledger(data):
    path = get_ledger_path()
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def init_db():
    _load_ledger() # Ensure it can load

def get_provider_state(provider: str, dataset: str, key: str) -> str:
    ledger = _load_ledger()
    return ledger.get("provider_state", {}).get(provider, {}).get(dataset, {}).get(key)

def set_provider_state(provider: str, dataset: str, key: str, value: str):
    ledger = _load_ledger()
    if "provider_state" not in ledger:
        ledger["provider_state"] = {}
    if provider not in ledger["provider_state"]:
        ledger["provider_state"][provider] = {}
    if dataset not in ledger["provider_state"][provider]:
        ledger["provider_state"][provider][dataset] = {}
        
    ledger["provider_state"][provider][dataset][key] = value
    _save_ledger(ledger)

def record_run_start(run_id: str, provider: str, dataset: str, mode: str, logical_date: str):
    ledger = _load_ledger()
    tz = pytz.timezone('Asia/Kolkata')
    
    if "runs" not in ledger:
        ledger["runs"] = {}
        
    ledger["runs"][run_id] = {
        "provider": provider,
        "dataset": dataset,
        "mode": mode,
        "logical_date": logical_date,
        "status": "RUNNING",
        "started_at": datetime.now(tz).isoformat()
    }
    _save_ledger(ledger)

def record_run_complete(run_id: str, records: int, bytes_written: int, raw_hash: str):
    ledger = _load_ledger()
    tz = pytz.timezone('Asia/Kolkata')
    
    if run_id in ledger.get("runs", {}):
        ledger["runs"][run_id].update({
            "status": "SUCCESS",
            "completed_at": datetime.now(tz).isoformat(),
            "records": records,
            "bytes_written": bytes_written,
            "raw_hash": raw_hash
        })
        _save_ledger(ledger)

def record_run_error(run_id: str, error_code: str):
    ledger = _load_ledger()
    tz = pytz.timezone('Asia/Kolkata')
    
    if run_id in ledger.get("runs", {}):
        ledger["runs"][run_id].update({
            "status": "FAILED",
            "completed_at": datetime.now(tz).isoformat(),
            "error_code": error_code
        })
        _save_ledger(ledger)
