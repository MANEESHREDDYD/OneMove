import datetime
import json
import os
import subprocess
from typing import Any, Dict, Tuple

import pandas as pd
import requests


def get_supabase_config() -> Tuple[str, str]:
    api_url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable missing")
    return api_url, key

def get_data_dirs() -> Dict[str, str]:
    data_root = os.environ.get("ZONEPILOT_DATA_ROOT")
    if not data_root:
        raise ValueError("ZONEPILOT_DATA_ROOT environment variable missing. Real research processing must not use repository data/.")
    
    dirs = {
        "raw": os.path.join(data_root, "private", "raw"),
        "bronze": os.path.join(data_root, "private", "bronze"),
        "silver": os.path.join(data_root, "private", "silver")
    }
    for p in dirs.values():
        os.makedirs(p, exist_ok=True)
    return dirs

def run_etl_pipeline() -> Dict[str, Any]:
    print("=== ZonePilot ETL Pipeline Execution ===")
    
    url, key = get_supabase_config()
    dirs = get_data_dirs()
    print(f"Data Roots -> Raw: {dirs['raw']}, Bronze: {dirs['bronze']}, Silver: {dirs['silver']}")
    
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    
    # 1. Snapshot Raw Layer
    print("\n--- Phase 1: Snapshot (Raw) ---")
    probe_resp = requests.get(f"{url}/rest/v1/probe_observations?select=*", headers=headers)
    probe_data = probe_resp.json() if probe_resp.status_code == 200 else []
    
    study_resp = requests.get(f"{url}/rest/v1/studies?select=id,study_phase", headers=headers)
    study_data = study_resp.json() if study_resp.status_code == 200 else []
    study_phase_map = {s["id"]: s.get("study_phase", "DRY_RUN") for s in study_data} if study_data else {}
    
    snapshot_id = f"snap_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    raw_dir = os.path.join(dirs["raw"], snapshot_id)
    os.makedirs(raw_dir, exist_ok=True)
    
    df_raw = pd.DataFrame(probe_data) if probe_data else pd.DataFrame(columns=[
        "id", "study_id", "assignment_id", "participant_id", "client_event_id", 
        "provenance", "eta_low_min", "eta_high_min", "option_count", "availability_state", 
        "zone_cluster", "platform", "protocol", "observed_at_device"
    ])
    
    # Resolve authoritative study_phase onto observation dataframe
    if not df_raw.empty and "study_id" in df_raw:
        df_raw["study_phase"] = df_raw["study_id"].map(study_phase_map).fillna("DRY_RUN")
    else:
        df_raw["study_phase"] = "DRY_RUN"
        
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    raw_hash = str(pd.util.hash_pandas_object(df_raw).sum()) if not df_raw.empty else "0"
    
    raw_parquet = os.path.join(raw_dir, "probe_observations.parquet")
    df_raw.to_parquet(raw_parquet, index=False)
    
    raw_manifest = {
        "snapshot_id": snapshot_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_tables": ["probe_observations", "studies"],
        "row_count": len(df_raw),
        "source_hash": raw_hash,
        "git_sha": git_sha
    }
    with open(os.path.join(raw_dir, "manifest.json"), "w") as f:
        json.dump(raw_manifest, f, indent=2)
        
    print(f"Raw Snapshot ID: {snapshot_id}, Rows: {len(df_raw)}, Hash: {raw_hash}")
    
    # 2. Bronze Layer (Parsing, Type Normalization, Deduplication)
    print("\n--- Phase 2: Bronze Layer ---")
    bronze_dir = os.path.join(dirs["bronze"], snapshot_id)
    os.makedirs(bronze_dir, exist_ok=True)
    
    input_bronze = len(df_raw)
    valid_mask = pd.Series(True, index=df_raw.index) if not df_raw.empty else pd.Series(dtype=bool)
    
    if not df_raw.empty:
        # Check constraints (non-null mandatory fields, valid provenance)
        valid_mask = df_raw['eta_low_min'].notnull() & df_raw['provenance'].isin(['OBSERVED', 'FIXTURE', 'SIMULATED', 'DERIVED'])
        df_bronze = df_raw[valid_mask].copy()
        
        # Deduplication on client_event_id
        if 'client_event_id' in df_bronze:
            df_bronze = df_bronze.drop_duplicates(subset=['client_event_id'])
    else:
        df_bronze = df_raw.copy()
        
    bronze_parquet = os.path.join(bronze_dir, "probe_observations.parquet")
    df_bronze.to_parquet(bronze_parquet, index=False)
    
    valid_count = len(df_bronze)
    rejected_count = input_bronze - valid_count
    
    print(f"Bronze Input: {input_bronze}, Valid: {valid_count}, Rejected: {rejected_count}")
    
    # 3. Silver Layer (Feature Normalization & Weather Join)
    print("\n--- Phase 3: Silver Layer ---")
    silver_dir = os.path.join(dirs["silver"], snapshot_id)
    os.makedirs(silver_dir, exist_ok=True)
    
    df_silver = df_bronze.copy()
    weather_matches = 0
    weather_misses = len(df_silver)
    missingness_pct = "100.0%" if len(df_silver) > 0 else "0.0%"
    
    if not df_silver.empty and 'weather_temperature' in df_silver:
        weather_matches = int(df_silver['weather_temperature'].notnull().sum())
        weather_misses = len(df_silver) - weather_matches
        missingness_pct = f"{round((weather_misses / len(df_silver)) * 100, 2)}%"
        
    silver_parquet = os.path.join(silver_dir, "probe_observations.parquet")
    df_silver.to_parquet(silver_parquet, index=False)
    
    print(f"Silver Output: {len(df_silver)}, Weather Matches: {weather_matches}, Misses: {weather_misses}, Missingness: {missingness_pct}")
    
    # 4. DQ Data Quality Gate
    print("\n--- Phase 4: Data Quality (DQ) Rule Suite ---")
    rules = []
    
    # Rule 1: No duplicate client_event_id
    r1 = not df_raw.duplicated(subset=['client_event_id']).any() if ('client_event_id' in df_raw and not df_raw.empty) else True
    rules.append({"id": "DQ-001", "name": "No duplicate client_event_id", "status": "PASS" if r1 else "FAIL"})
    
    # Rule 2: ETA high >= ETA low
    if not df_raw.empty and 'eta_high_min' in df_raw and 'eta_low_min' in df_raw:
        valid_eta = df_raw['eta_high_min'].notnull() & df_raw['eta_low_min'].notnull()
        r2 = bool((df_raw.loc[valid_eta, 'eta_high_min'] >= df_raw.loc[valid_eta, 'eta_low_min']).all()) if valid_eta.any() else True
    else:
        r2 = True
    rules.append({"id": "DQ-002", "name": "ETA high >= ETA low", "status": "PASS" if r2 else "FAIL"})
    
    # Rule 3: Non-negative ETA low
    r3 = bool((df_raw['eta_low_min'] >= 0).all()) if (not df_raw.empty and 'eta_low_min' in df_raw and df_raw['eta_low_min'].notnull().any()) else True
    rules.append({"id": "DQ-003", "name": "Non-negative ETA low", "status": "PASS" if r3 else "FAIL"})
    
    # Rule 4: Non-negative Option Count
    r4 = bool((df_raw['option_count'] >= 0).all()) if (not df_raw.empty and 'option_count' in df_raw and df_raw['option_count'].notnull().any()) else True
    rules.append({"id": "DQ-004", "name": "Non-negative Option Count", "status": "PASS" if r4 else "FAIL"})
    
    # Rule 5: Valid Protocol (ANCHOR/BURST)
    r5 = bool(df_raw['protocol'].isin(['ANCHOR', 'BURST']).all()) if (not df_raw.empty and 'protocol' in df_raw) else True
    rules.append({"id": "DQ-005", "name": "Valid Protocol (ANCHOR/BURST)", "status": "PASS" if r5 else "FAIL"})

    # Rule 6: Known Zone Cluster
    r6 = bool(df_raw['zone_cluster'].notnull().all()) if (not df_raw.empty and 'zone_cluster' in df_raw) else True
    rules.append({"id": "DQ-006", "name": "Known Zone Cluster", "status": "PASS" if r6 else "FAIL"})
    
    dq_passed = True
    for r in rules:
        print(f"Rule {r['id']} ({r['name']}): {r['status']}")
        if r['status'] == "FAIL":
            dq_passed = False

    if not dq_passed:
        print("\n❌ ETL Pipeline DQ validation failed!")
    else:
        print("\n✅ ETL Pipeline execution completed successfully.")
        
    return {
        "snapshot_id": snapshot_id,
        "dq_passed": dq_passed,
        "raw_rows": len(df_raw),
        "silver_rows": len(df_silver),
        "rules": rules
    }

def build_experiment_a_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dataset builder for Experiment A.
    Fails closed if any DRY_RUN phase rows are present.
    """
    if 'study_phase' in df and (df['study_phase'] == 'DRY_RUN').any():
        dry_run_count = (df['study_phase'] == 'DRY_RUN').sum()
        raise ValueError(f"CRITICAL: Experiment A dataset builder failed closed. Found {dry_run_count} DRY_RUN rows in dataset.")
    return df[df['study_phase'] == 'EXPERIMENT_A'].copy() if 'study_phase' in df else df

if __name__ == "__main__":
    run_etl_pipeline()
