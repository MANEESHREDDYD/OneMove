import requests
import json
import os
import pandas as pd
import uuid
import datetime
import subprocess

def get_supabase_config():
    api_url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable missing")
    return api_url, key

def get_data_root():
    data_root = os.environ.get("ZONEPILOT_DATA_ROOT")
    if not data_root:
        raise ValueError("ZONEPILOT_DATA_ROOT environment variable missing. Real research processing must not use repository data/.")
    private_raw = os.path.join(data_root, "private", "raw")
    os.makedirs(private_raw, exist_ok=True)
    return private_raw

def run_etl_pipeline():
    print("=== ZonePilot ETL Pipeline Execution ===")
    
    url, key = get_supabase_config()
    private_raw = get_data_root()
    print(f"Data Root Raw Path: {private_raw}")
    
    # 1. Snapshot
    print("\n--- Phase 1: Snapshot ---")
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    resp = requests.get(f"{url}/rest/v1/probe_observations?select=*", headers=headers)
    data = resp.json() if resp.status_code == 200 else []
    
    snapshot_id = f"snap_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    snapshot_dir = os.path.join(private_raw, snapshot_id)
    os.makedirs(snapshot_dir, exist_ok=True)
    
    df = pd.DataFrame(data) if data else pd.DataFrame(columns=["id", "participant_id", "provenance", "eta_low_min", "eta_high_min", "zone_cluster", "protocol", "study_phase", "observed_at_device"])
    df_hash = str(pd.util.hash_pandas_object(df).sum()) if not df.empty else "0"
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    
    raw_file = os.path.join(snapshot_dir, "probe_observations.parquet")
    df.to_parquet(raw_file, index=False)
    
    manifest = {
        "snapshot_id": snapshot_id,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "source_tables": ["probe_observations"],
        "row_counts": {"probe_observations": len(df)},
        "schema_version": "1.5.1",
        "source_hash": df_hash,
        "git_sha": git_sha
    }
    manifest_path = os.path.join(snapshot_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Snapshot ID: {snapshot_id}")
    print(f"Rows: probe_observations={len(df)}")
    print(f"Hash: {df_hash}")
    print(f"Git SHA: {git_sha}")
    print(f"Manifest written to: {manifest_path}")
    
    # 2. Bronze
    print("\n--- Phase 2: Bronze ---")
    input_bronze = len(df)
    valid = 0
    flagged = 0
    rejected = 0
    deduplicated = 0
    
    if not df.empty:
        # Check constraints (non-null mandatory fields, valid provenance)
        df['is_valid'] = df['eta_low_min'].notnull() & df['provenance'].isin(['OBSERVED', 'FIXTURE', 'SIMULATED', 'DERIVED'])
        valid = int(df['is_valid'].sum())
        rejected = len(df) - valid
        # Deduplication on client_event_id if column exists
        if 'client_event_id' in df:
            deduplicated = len(df) - len(df.drop_duplicates(subset=['client_event_id']))
    
    print(f"Input: {input_bronze}")
    print(f"Valid: {valid}")
    print(f"Flagged: {flagged}")
    print(f"Rejected: {rejected}")
    print(f"Deduplicated: {deduplicated}")
    
    # 3. Silver
    print("\n--- Phase 3: Silver ---")
    input_silver = valid
    weather_matches = 0
    misses = 0
    missingness = "0.0%"
    
    if not df.empty:
        df_silver = df[df['is_valid']].copy()
        output_silver = len(df_silver)
        # Real weather join evaluation
        if 'weather_temperature' in df_silver:
            weather_matches = int(df_silver['weather_temperature'].notnull().sum())
            misses = output_silver - weather_matches
            missingness = f"{round((misses / output_silver) * 100, 2)}%" if output_silver > 0 else "0.0%"
        else:
            misses = output_silver
            missingness = "100.0%" if output_silver > 0 else "0.0%"
    else:
        output_silver = 0
        
    print(f"Input: {input_silver}")
    print(f"Output: {output_silver}")
    print(f"Weather matches: {weather_matches}")
    print(f"Misses: {misses}")
    print(f"Missingness: {missingness}")
    
    # 4. DQ (Data Quality)
    print("\n--- Phase 4: DQ (Data Quality) ---")
    rules = []
    
    # Rule 1: No duplicate client_event_id
    if not df.empty and 'client_event_id' in df:
        r1_pass = not df.duplicated(subset=['client_event_id']).any()
    else:
        r1_pass = True
    rules.append({"rule": "DQ-001: No duplicate client_event_id", "result": "PASS" if r1_pass else "FAIL"})
    
    # Rule 2: ETA high >= ETA low
    if not df.empty and 'eta_high_min' in df and 'eta_low_min' in df:
        valid_eta_rows = df['eta_high_min'].notnull() & df['eta_low_min'].notnull()
        if valid_eta_rows.any():
            r2_pass = bool((df.loc[valid_eta_rows, 'eta_high_min'] >= df.loc[valid_eta_rows, 'eta_low_min']).all())
        else:
            r2_pass = True
    else:
        r2_pass = True
    rules.append({"rule": "DQ-002: ETA high >= ETA low", "result": "PASS" if r2_pass else "FAIL"})
    
    # Rule 3: Known zone_cluster non-empty
    if not df.empty and 'zone_cluster' in df:
        r3_pass = bool(df['zone_cluster'].notnull().all())
    else:
        r3_pass = True
    rules.append({"rule": "DQ-003: Known zone_cluster formats", "result": "PASS" if r3_pass else "FAIL"})
    
    # Rule 4: Valid protocol (ANCHOR/BURST)
    if not df.empty and 'protocol' in df:
        r4_pass = bool(df['protocol'].isin(['ANCHOR', 'BURST']).all())
    else:
        r4_pass = True
    rules.append({"rule": "DQ-004: Valid protocol (ANCHOR/BURST)", "result": "PASS" if r4_pass else "FAIL"})
    
    dq_passed = True
    for r in rules:
        print(f"Rule {r['rule']}: {r['result']}")
        if r['result'] == "FAIL":
            dq_passed = False

    if not dq_passed:
        print("\n❌ ETL Pipeline DQ validation failed!")
    else:
        print("\n✅ ETL Pipeline execution completed successfully.")
        
    return {"snapshot_id": snapshot_id, "dq_passed": dq_passed, "rows": len(df)}

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
