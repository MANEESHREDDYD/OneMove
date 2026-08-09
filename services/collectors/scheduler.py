from datetime import datetime

import pytz

from services.collectors.context.ondc import run_ondc_collection
from services.collectors.context.openmeteo import run_openmeteo_collection
from services.collectors.manifests import generate_daily_manifest
from services.collectors.platforms.swiggy.food import run_swiggy_food_collection
from services.collectors.platforms.zomato.pos_client import run_zomato_pos_collection
from services.collectors.traffic.tomtom.client import run_tomtom_traffic_collection


def run_all_collectors():
    """Execute all active, keyless, and keyed (if ready) collectors."""
    print("Starting ZonePilot Master Collection Scheduler...")
    
    # 1. Open-Meteo (ACTIVE_REAL)
    print("Executing Open-Meteo Collector...")
    try:
        run_openmeteo_collection()
    except Exception as e:
        print(f"Open-Meteo Collector Failed: {e}")
        
    # 2. ONDC (ACTIVE_REAL)
    print("Executing ONDC Collector...")
    try:
        run_ondc_collection()
    except Exception as e:
        print(f"ONDC Collector Failed: {e}")
        
    # 3. Swiggy Food (READY_NEEDS_SWIGGY_OAUTH_OR_PRODUCTION_ACCESS)
    print("Executing Swiggy Food Collector...")
    try:
        run_swiggy_food_collection()
    except Exception as e:
        print(f"Swiggy Collector Skipped/Failed: {e}")

    # 4. Zomato (READY_NEEDS_OFFICIAL_ZOMATO_ACCESS)
    print("Executing Zomato Collector...")
    try:
        run_zomato_pos_collection()
    except Exception as e:
        print(f"Zomato Collector Skipped/Failed: {e}")
        
    # 5. TomTom (READY_NEEDS_API_KEY)
    print("Executing TomTom Collector...")
    try:
        run_tomtom_traffic_collection()
    except Exception as e:
        print(f"TomTom Collector Skipped/Failed: {e}")
        
    # Finalize logical day manifest
    logical_date = datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%Y-%m-%d')
    generate_daily_manifest(logical_date)

if __name__ == "__main__":
    run_all_collectors()
