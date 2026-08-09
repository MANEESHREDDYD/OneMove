import os

from services.collectors.context.openmeteo import run_openmeteo_intraday
from services.collectors.traffic.tomtom.client import run_tomtom_intraday
# Live order trackers would be added here

def run_intraday_collectors():
    """Execute intraday snapshots (live traffic, prospective weather forecasts).
    This script is designed to be executed every 5-15 minutes by a cron job or task scheduler.
    """
    print("Starting ZonePilot INTRADAY Collection Scheduler...")
    
    print("Executing Open-Meteo Forecast Snapshots...")
    try:
        run_openmeteo_intraday()
    except Exception as e:
        print(f"Open-Meteo Intraday Failed: {e}")
        
    print("Executing TomTom Live Traffic Routing...")
    try:
        run_tomtom_intraday()
    except Exception as e:
        print(f"TomTom Intraday Failed: {e}")

if __name__ == "__main__":
    run_intraday_collectors()
