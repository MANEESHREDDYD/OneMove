import json
import os
from datetime import datetime, timedelta

import pytz


def get_ledger_path():
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    return os.path.join(repo_root, "data", "rolling", "dataset_registry.json")

def enforce_retention():
    path = get_ledger_path()
    if not os.path.exists(path):
        print("No rolling ledger found.")
        return

    with open(path, 'r') as f:
        ledger = json.load(f)

    tz = pytz.timezone('Asia/Kolkata')
    now_local = datetime.now(tz)
    
    # 365 rolling days: Cutoff is (now - 364 days). If today is Day 366, Day 1 is 365 days old (so < cutoff).
    # Wait, the rule is `retention_cutoff = logical_date - 364 days`.
    logical_date = now_local.date()
    cutoff_date = logical_date - timedelta(days=364)
    cutoff_str = cutoff_date.strftime('%Y-%m-%d')
    
    print(f"Current Logical Date: {logical_date}")
    print(f"Retention Cutoff (365 active days): {cutoff_str}")

    runs = ledger.get("runs", {})
    keys_to_delete = []

    for run_id, run_data in runs.items():
        run_logical = run_data.get("logical_date")
        if run_logical and run_logical < cutoff_str:
            keys_to_delete.append(run_id)

    if keys_to_delete:
        print(f"Deleting {len(keys_to_delete)} expired runs from the active registry.")
        for k in keys_to_delete:
            del runs[k]
        
        with open(path, 'w') as f:
            json.dump(ledger, f, indent=2)
        print("Successfully pruned dataset_registry.json.")
    else:
        print("No expired runs found. Registry is within the 365-day rolling window.")

if __name__ == "__main__":
    enforce_retention()
