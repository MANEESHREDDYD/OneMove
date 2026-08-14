import sys

from services.collectors.context.openmeteo import run_openmeteo_intraday
from services.collectors.traffic.tomtom.client import run_tomtom_intraday


def run_intraday_collectors():
    """Execute intraday snapshots (live traffic, prospective weather forecasts)."""
    print("Starting ZonePilot INTRADAY Collection Scheduler...")
    
    has_failure = False
    
    print("Executing Open-Meteo Forecast Snapshots...")
    try:
        run_openmeteo_intraday()
    except Exception as e:
        print(f"Open-Meteo Intraday Failed: {e}")
        has_failure = True
        
    print("Executing TomTom Live Traffic Routing...")
    try:
        run_tomtom_intraday()
    except Exception as e:
        if "READY_NEEDS_API_KEY" in str(e):
            print("TomTom Intraday: Skipped (Not configured)")
        else:
            print(f"TomTom Intraday Failed: {e}")
            has_failure = True

    if has_failure:
        print("Scheduler exiting with failure due to provider errors.")
        sys.exit(1)

if __name__ == "__main__":
    run_intraday_collectors()
