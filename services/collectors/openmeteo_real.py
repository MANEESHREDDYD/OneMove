import datetime
import hashlib
import json
import os
import tempfile
import time
from typing import Any, Dict, Optional

import pandas as pd
import requests


def get_target_dir(subpath: str) -> str:
    data_root = os.environ.get("ZONEPILOT_DATA_ROOT")
    if not data_root:
        # Fallback to system temp directory for unit tests
        data_root = os.path.join(tempfile.gettempdir(), "zonepilot_data")
    path = os.path.join(data_root, "private", "raw", "open-meteo", subpath)
    os.makedirs(path, exist_ok=True)
    return path

def select_point_in_time_forecast(forecasts_df: pd.DataFrame, prediction_time: pd.Timestamp, valid_time: pd.Timestamp) -> Optional[Dict[str, Any]]:
    """
    Selects the most recent forecast issued ON OR BEFORE prediction_time that is valid at valid_time.
    Strictly rejects any forecast issued AFTER prediction_time to prevent future data leakage.
    """
    if forecasts_df.empty:
        return None
    
    # Filter for target valid_at
    valid_matches = forecasts_df[forecasts_df['valid_at'] == valid_time].copy()
    if valid_matches.empty:
        return None
    
    # Filter for issued_at <= prediction_time (LEAKAGE PREVENTION)
    eligible = valid_matches[valid_matches['issued_at'] <= prediction_time]
    if eligible.empty:
        return None
    
    # Pick latest issued_at among eligible
    eligible = eligible.sort_values(by='issued_at', ascending=False)
    return eligible.iloc[0].to_dict()

def run_openmeteo_collection(start_date: str = "2025-08-08", end_date: str = "2026-08-07"):
    print("=== Open-Meteo Collector Evidence ===")
    latitude, longitude = 12.9716, 77.5946  # Bengaluru
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,precipitation,rain,weather_code,wind_speed_10m",
        "timezone": "Asia/Kolkata"
    }
    
    print(f"Requesting observed/reanalysis history for Bengaluru from {start_date} to {end_date}...")
    start_time = time.time()
    
    # Retries and timeout
    response = None
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                break
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(1)
            
    if not response or response.status_code != 200:
        print("Error fetching Open-Meteo data after retries")
        return None
        
    data = response.json()
    if "error" in data:
        print(f"Error fetching data: {data}")
        return None
        
    hourly = data["hourly"]
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    
    # Expected hourly timestamp range validation (Asia/Kolkata timezone)
    expected_times = pd.date_range(start=f"{start_date} 00:00", end=f"{end_date} 23:00", freq="1h", tz="Asia/Kolkata")
    
    # Normalize returned timestamps to Asia/Kolkata timezone
    if df["time"].dt.tz is None:
        actual_times = df["time"].dt.tz_localize("Asia/Kolkata")
    else:
        actual_times = df["time"].dt.tz_convert("Asia/Kolkata")
        
    returned_rows = len(df)
    missing_timestamps = len(set(expected_times) - set(actual_times))
    duplicate_timestamps = int(actual_times.duplicated().sum())
    rows_with_nulls = int(df.isnull().any(axis=1).sum())
    
    out_dir = get_target_dir("observed")
    out_path = os.path.join(out_dir, f"{start_date}_{end_date}.parquet")
    df.to_parquet(out_path, index=False)
    
    with open(out_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
        
    run_id = f"run_om_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    manifest = {
        "run_id": run_id,
        "requested_range": f"{start_date} -> {end_date}",
        "returned_rows": returned_rows,
        "expected_rows": len(expected_times),
        "missing_timestamps": missing_timestamps,
        "duplicate_timestamps": duplicate_timestamps,
        "rows_with_nulls": rows_with_nulls,
        "parquet_path": out_path,
        "parquet_sha256": file_hash,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    manifest_path = os.path.join(out_dir, f"{run_id}_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    print(f"Returned range: {df['time'].min()} -> {df['time'].max()}")
    print(f"Hourly rows: {returned_rows}")
    print(f"Expected rows: {len(expected_times)}")
    print(f"Missing timestamps: {missing_timestamps}")
    print(f"Duplicate timestamps: {duplicate_timestamps}")
    print(f"Rows with nulls: {rows_with_nulls}")
    print(f"Run ID: {run_id}")
    print(f"Manifest SHA256: {file_hash}")
    print(f"Execution time: {time.time() - start_time:.2f}s")
    
    return manifest

if __name__ == "__main__":
    run_openmeteo_collection()
