import sys
from datetime import datetime

import pytz

from services.collectors.context.openmeteo import run_openmeteo_midnight
from services.collectors.context.osm import run_osm_midnight
from services.collectors.manifests import generate_daily_manifest
from services.collectors.traffic.tomtom.client import run_tomtom_midnight


def run_midnight_collectors():
    """Execute all daily rollover and baseline acquisition tasks (00:00 IST)."""
    print("Starting ZonePilot MIDNIGHT Collection Scheduler...")

    has_failure = False

    print("Executing Open-Meteo Historical/Archive...")
    try:
        run_openmeteo_midnight()
    except Exception as e:
        print(f"Open-Meteo Midnight Failed: {e}")
        has_failure = True

    print("Executing OSM Upstream Check...")
    try:
        run_osm_midnight()
    except Exception as e:
        print(f"OSM Midnight Failed: {e}")
        has_failure = True

    print("Executing TomTom Historical/Archive...")
    try:
        run_tomtom_midnight()
    except Exception as e:
        if "READY_NEEDS_TRAFFIC_STATS_SUBSCRIPTION" in str(e):
            print("TomTom Traffic Stats: Skipped (Not configured)")
        else:
            print(f"TomTom Midnight Failed: {e}")
            has_failure = True

    # Generate manifest for previous day
    tz = pytz.timezone("Asia/Kolkata")
    logical_date = datetime.now(tz).strftime("%Y-%m-%d")
    generate_daily_manifest(logical_date)

    if has_failure:
        print("Scheduler exiting with failure due to provider errors.")
        sys.exit(1)


if __name__ == "__main__":
    run_midnight_collectors()
