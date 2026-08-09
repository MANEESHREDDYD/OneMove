import os
from datetime import datetime
import pytz

from services.collectors.context.openmeteo import run_openmeteo_midnight
from services.collectors.context.osm import run_osm_midnight
from services.collectors.traffic.tomtom.client import run_tomtom_midnight
from services.collectors.manifests import generate_daily_manifest
# Swiggy/Zomato/ONDC would be added here when applicable

def run_midnight_collectors():
    """Execute all daily rollover and baseline acquisition tasks (00:00 IST)."""
    print("Starting ZonePilot MIDNIGHT Collection Scheduler...")
    
    print("Executing Open-Meteo Historical/Archive...")
    try:
        run_openmeteo_midnight()
    except Exception as e:
        print(f"Open-Meteo Midnight Failed: {e}")

    print("Executing OSM Upstream Check...")
    try:
        run_osm_midnight()
    except Exception as e:
        print(f"OSM Midnight Failed: {e}")
        
    print("Executing TomTom Historical/Archive...")
    try:
        run_tomtom_midnight()
    except Exception as e:
        print(f"TomTom Midnight Failed: {e}")
        
    # Generate manifest for previous day
    tz = pytz.timezone('Asia/Kolkata')
    # Because this runs at 00:00 or shortly after, we manifest the day that just ended.
    # However, to be perfectly safe, we might just use the current logical date or date-1.
    # We will let the manifest script handle logic.
    logical_date = datetime.now(tz).strftime('%Y-%m-%d')
    generate_daily_manifest(logical_date)

if __name__ == "__main__":
    run_midnight_collectors()
