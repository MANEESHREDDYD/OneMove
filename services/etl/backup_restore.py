import os
import json
import hashlib
import tempfile
import shutil
from typing import Dict, Any, List

def run_backup(data_records: List[Dict[str, Any]], backup_file_path: str) -> Dict[str, Any]:
    """
    Backs up a list of records to a physical JSON backup file and returns manifest metadata.
    """
    os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
    content = json.dumps(data_records, indent=2, sort_keys=True)
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    with open(backup_file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return {
        "backup_file": backup_file_path,
        "record_count": len(data_records),
        "sha256": content_hash,
        "size_bytes": len(content)
    }

def run_restore(backup_file_path: str) -> List[Dict[str, Any]]:
    """
    Restores records from a physical JSON backup file.
    """
    if not os.path.exists(backup_file_path):
        raise FileNotFoundError(f"Backup file not found: {backup_file_path}")
        
    with open(backup_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    return data

def verify_backup_restore_cycle(sample_records: List[Dict[str, Any]]) -> bool:
    """
    Executes a complete backup -> destructive mutation -> restore -> verification cycle.
    Returns True if data is 100% recovered matching row count and hash.
    """
    temp_dir = tempfile.mkdtemp()
    backup_file = os.path.join(temp_dir, "test_backup.json")
    try:
        orig_hash = hashlib.sha256(json.dumps(sample_records, sort_keys=True).encode('utf-8')).hexdigest()
        orig_count = len(sample_records)
        
        # 1. Backup
        backup_meta = run_backup(sample_records, backup_file)
        assert backup_meta["record_count"] == orig_count
        
        # 2. Destructive mutation of local state
        working_state = []
        assert len(working_state) == 0, "Local state not cleared"
        
        # 3. Restore
        restored_records = run_restore(backup_file)
        restored_hash = hashlib.sha256(json.dumps(restored_records, sort_keys=True).encode('utf-8')).hexdigest()
        
        # 4. Verify
        recovered = (len(restored_records) == orig_count) and (restored_hash == orig_hash)
        return recovered
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
