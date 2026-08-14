import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

import httpx
import pytz

from services.collectors.db import (
    get_provider_state,
    init_db,
    record_run_complete,
    record_run_error,
    record_run_start,
    set_provider_state,
)
from services.collectors.storage import ensure_directories, save_bronze_data, save_raw_data, save_silver_data

TIMEZONE = "Asia/Kolkata"

# Spatial sampling plan for Bengaluru Pilot Corridor (HSR, Koramangala, Indiranagar)
# Instead of one point, we query 3 representative H3-ish points
SAMPLING_POINTS = [
    {"point_id": "hsr", "lat": 12.9141, "lon": 77.6358},
    {"point_id": "krm", "lat": 12.9348, "lon": 77.6200},
    {"point_id": "ind", "lat": 12.9780, "lon": 77.6400}
]

def fetch_openmeteo_historical(lat: float, lon: float, start_date: str, end_date: str) -> Dict[str, Any]:
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": "temperature_2m,apparent_temperature,precipitation,rain,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,cloud_cover,weather_code,surface_pressure,visibility",
        "timezone": TIMEZONE
    }
    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()

def fetch_openmeteo_forecast(lat: float, lon: float) -> Dict[str, Any]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,apparent_temperature,precipitation,rain,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,cloud_cover,weather_code,surface_pressure,visibility",
        "timezone": TIMEZONE,
        "past_days": 0,
        "forecast_days": 2
    }
    with httpx.Client() as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()

def process_bronze_weather(raw_data: Dict[str, Any], retrieved_at: str, run_id: str, point_id: str, evidence_class: str) -> List[Dict[str, Any]]:
    hourly = raw_data.get('hourly', {})
    times = hourly.get('time', [])
    
    bronze = []
    for i in range(len(times)):
        record = {
            "time": times[i],
            "point_id": point_id,
            "temperature_2m": hourly.get('temperature_2m', [])[i] if 'temperature_2m' in hourly else None,
            "apparent_temperature": hourly.get('apparent_temperature', [])[i] if 'apparent_temperature' in hourly else None,
            "precipitation": hourly.get('precipitation', [])[i] if 'precipitation' in hourly else None,
            "rain": hourly.get('rain', [])[i] if 'rain' in hourly else None,
            "relative_humidity_2m": hourly.get('relative_humidity_2m', [])[i] if 'relative_humidity_2m' in hourly else None,
            "wind_speed_10m": hourly.get('wind_speed_10m', [])[i] if 'wind_speed_10m' in hourly else None,
            "wind_gusts_10m": hourly.get('wind_gusts_10m', [])[i] if 'wind_gusts_10m' in hourly else None,
            "cloud_cover": hourly.get('cloud_cover', [])[i] if 'cloud_cover' in hourly else None,
            "weather_code": hourly.get('weather_code', [])[i] if 'weather_code' in hourly else None,
            "surface_pressure": hourly.get('surface_pressure', [])[i] if 'surface_pressure' in hourly else None,
            "visibility": hourly.get('visibility', [])[i] if 'visibility' in hourly else None,
            "_provenance": {
                "provider": "openmeteo",
                "run_id": run_id,
                "retrieved_at": retrieved_at,
                "evidence_class": evidence_class
            }
        }
        bronze.append(record)
    return bronze

def process_silver_weather(bronze_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    silver = []
    for record in bronze_data:
        dt = datetime.fromisoformat(record['time'])
        if dt.tzinfo is None:
            tz = pytz.timezone(TIMEZONE)
            dt = tz.localize(dt)
            
        retrieved_at = datetime.fromisoformat(record['_provenance']['retrieved_at'])
            
        silver_record = {
            "weather_event_id": f"OM-{record['point_id']}-{dt.isoformat()}",
            "point_id": record['point_id'],
            "event_time": dt.isoformat(),
            "information_available_at": retrieved_at.isoformat(),
            "temperature_c": record['temperature_2m'],
            "feels_like_c": record['apparent_temperature'],
            "precipitation_mm": record['precipitation'],
            "humidity_pct": record['relative_humidity_2m'],
            "wind_speed_kmh": record['wind_speed_10m'],
            "weather_code": record['weather_code'],
            "_provenance": record['_provenance']
        }
        silver.append(silver_record)
    return silver

def run_openmeteo_midnight():
    """Historical archive collection run once daily at midnight to capture the previous day definitively."""
    init_db()
    ensure_directories()
    
    provider = "openmeteo"
    dataset = "weather_historical"
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    
    last_fetched = get_provider_state(provider, dataset, "last_fetched_date")
    if not last_fetched:
        start_date = (now - timedelta(days=365)).strftime('%Y-%m-%d')
        mode = "HISTORICAL_BACKFILL"
    else:
        last_dt = datetime.strptime(last_fetched, '%Y-%m-%d').date()
        start_date = (last_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        mode = "PROSPECTIVE_LIVE"
        
    end_date = (now - timedelta(days=1)).strftime('%Y-%m-%d') 
    
    if start_date > end_date:
        print("Open-Meteo Historical: Already up to date.")
        return

    run_id = str(uuid.uuid4())
    logical_date = now.strftime('%Y-%m-%d')
    
    try:
        record_run_start(run_id, provider, dataset, mode, logical_date)
        total_written = 0
        
        for pt in SAMPLING_POINTS:
            raw_data = fetch_openmeteo_historical(pt['lat'], pt['lon'], start_date, end_date)
            save_raw_data(provider, dataset, now, run_id, raw_data, f"raw_historical_{pt['point_id']}.json")
            
            retrieved_at = now.isoformat()
            bronze_data = process_bronze_weather(raw_data, retrieved_at, run_id, pt['point_id'], "OFFICIAL_ARCHIVE")
            save_bronze_data(provider, dataset, now, run_id, bronze_data, f"bronze_{pt['point_id']}.jsonl")
            
            silver_data = process_silver_weather(bronze_data)
            save_silver_data(provider, dataset, now, run_id, silver_data, f"silver_{pt['point_id']}.jsonl")
            total_written += len(silver_data)
            
        record_run_complete(run_id, total_written, total_written, None) # Raw hash varied per point
        set_provider_state(provider, dataset, "last_fetched_date", end_date)
        print(f"[{run_id}] Success historical. Saved {total_written} records.")
    except Exception as e:
        print(f"[{run_id}] Failed historical: {str(e)}")
        record_run_error(run_id, "EXCEPTION")

def run_openmeteo_intraday():
    """Intraday live forecast snapshots for Shadow Operations."""
    init_db()
    ensure_directories()
    
    provider = "openmeteo"
    dataset = "weather_forecast_snapshots"
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    
    run_id = str(uuid.uuid4())
    logical_date = now.strftime('%Y-%m-%d')
    mode = "PROSPECTIVE_LIVE"
    
    try:
        record_run_start(run_id, provider, dataset, mode, logical_date)
        total_written = 0
        
        for pt in SAMPLING_POINTS:
            raw_data = fetch_openmeteo_forecast(pt['lat'], pt['lon'])
            save_raw_data(provider, dataset, now, run_id, raw_data, f"raw_forecast_{pt['point_id']}.json")
            
            retrieved_at = now.isoformat()
            bronze_data = process_bronze_weather(raw_data, retrieved_at, run_id, pt['point_id'], "PROVIDER_ESTIMATED")
            save_bronze_data(provider, dataset, now, run_id, bronze_data, f"bronze_fcst_{pt['point_id']}.jsonl")
            
            silver_data = process_silver_weather(bronze_data)
            save_silver_data(provider, dataset, now, run_id, silver_data, f"silver_fcst_{pt['point_id']}.jsonl")
            total_written += len(silver_data)
            
        record_run_complete(run_id, total_written, total_written, None)
        print(f"[{run_id}] Success forecast snapshot. Saved {total_written} records.")
    except Exception as e:
        print(f"[{run_id}] Failed forecast: {str(e)}")
        record_run_error(run_id, "EXCEPTION")

if __name__ == "__main__":
    run_openmeteo_midnight()
    run_openmeteo_intraday()
