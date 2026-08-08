import argparse
import requests
import pandas as pd
import datetime
import os
import sys

def fetch_openmeteo_history(start_date: str, end_date: str, output_dir: str):
    # Bengaluru coordinates
    lat = 12.9716
    lon = 77.5946
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,cloud_cover,surface_pressure,wind_speed_10m,wind_gusts_10m",
        "timezone": "Asia/Kolkata"
    }
    
    print(f"Fetching historical weather for {start_date} to {end_date}...")
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        return False
        
    data = response.json()
    
    if "hourly" not in data:
        print("Error: No hourly data returned.")
        return False
        
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    
    os.makedirs(output_dir, exist_ok=True)
    out_file = os.path.join(output_dir, f"weather_observed_{start_date}_{end_date}.parquet")
    
    df.to_parquet(out_file)
    print(f"Successfully wrote {len(df)} rows to {out_file}")
    
    # DQ Checks
    missing = df.isnull().sum().sum()
    print(f"DQ: Missing values: {missing}")
    
    if len(df) > 0:
        print(f"Time range covered: {df['time'].min()} to {df['time'].max()}")
        
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--outdir', default='data/bronze/weather')
    args = parser.parse_args()
    
    success = fetch_openmeteo_history(args.start, args.end, args.outdir)
    sys.exit(0 if success else 1)
