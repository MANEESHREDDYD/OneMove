import requests
import pandas as pd
import hashlib
import time
import json
import os

def run_openmeteo_collection():
    print("=== Open-Meteo Collector Evidence ===")
    start_date = "2025-08-08"
    end_date = "2026-08-07"
    latitude, longitude = 12.9716, 77.5946 # Bengaluru
    
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
    response = requests.get(url, params=params)
    data = response.json()
    
    if "error" in data:
        print(f"Error fetching data: {data}")
        return
        
    hourly = data["hourly"]
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"])
    
    # Calculate stats
    expected_rows = 365 * 24 # exactly one year
    returned_rows = len(df)
    missing_hours = df.isnull().any(axis=1).sum()
    duplicates = df.duplicated(subset=["time"]).sum()
    
    # Save to parquet
    out_dir = "data/bronze/open-meteo/observed"
    os.makedirs(out_dir, exist_ok=True)
    out_path = f"{out_dir}/2025-08-08_2026-08-07.parquet"
    df.to_parquet(out_path, index=False)
    
    # Calculate SHA256 of the parquet file
    with open(out_path, "rb") as f:
        manifest_sha256 = hashlib.sha256(f.read()).hexdigest()
        
    print(f"Requested range: {start_date} -> {end_date}")
    print(f"Returned range: {df['time'].min()} -> {df['time'].max()}")
    print(f"Hourly rows: {returned_rows}")
    print(f"Expected rows: {expected_rows}")
    print(f"Missing hours: {missing_hours}")
    print(f"Duplicates: {duplicates}")
    print(f"Partition count: 1")
    print(f"Run ID: run_om_20260808_100")
    print(f"Manifest SHA256: {manifest_sha256}")
    print(f"Execution time: {time.time() - start_time:.2f}s")
    
if __name__ == "__main__":
    run_openmeteo_collection()
