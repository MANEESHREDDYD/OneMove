import pandas as pd
from services.collectors.openmeteo_real import select_point_in_time_forecast
from services.api.scheduler import job_midnight, job_midnight_five
from services.etl.backup_restore import verify_backup_restore_cycle
from services.etl.pipeline import build_experiment_a_dataset

def test_weather_leakage():
    print("\n--- Executing Point-in-Time Weather Leakage Test ---")
    prediction_time = pd.Timestamp("2026-08-08 18:00:00+05:30")
    valid_time = pd.Timestamp("2026-08-08 19:00:00+05:30")
    
    forecasts = pd.DataFrame([
        {"id": "forecast_valid", "issued_at": pd.Timestamp("2026-08-08 17:30:00+05:30"), "valid_at": valid_time, "temp": 24.5},
        {"id": "forecast_future", "issued_at": pd.Timestamp("2026-08-08 18:05:00+05:30"), "valid_at": valid_time, "temp": 28.0}
    ])
    
    selected = select_point_in_time_forecast(forecasts, prediction_time, valid_time)
    assert selected is not None and selected["id"] == "forecast_valid"
    print("Result: PASS (Future forecast 18:05 correctly rejected at 18:00 prediction time)")

def test_scheduler_execution():
    print("\n--- Executing Scheduler Test ---")
    res_0000 = job_midnight("2026-08-08")
    assert res_0000["status"] == "SUCCESS"
    res_0005 = job_midnight_five("2026-08-08")
    assert res_0005["status"] == "SUCCESS"
    print("Result: PASS (Scheduler 00:00 and 00:05 jobs completed successfully)")

def test_backup_restore():
    print("\n--- Executing Backup/Restore Verification Test ---")
    sample_records = [
        {"id": "probe-1", "assignment_id": "assign-1", "provenance": "OBSERVED", "eta_low_min": 10},
        {"id": "probe-2", "assignment_id": "assign-2", "provenance": "OBSERVED", "eta_low_min": 15}
    ]
    recovered = verify_backup_restore_cycle(sample_records)
    assert recovered is True
    print("Result: PASS (Backup, destructive wipe, restore, and hash verification completed successfully)")
    
def test_dry_run_exclusion():
    print("\n--- Executing DRY_RUN Exclusion Test ---")
    df_clean = pd.DataFrame([{"id": "1", "study_phase": "EXPERIMENT_A"}])
    res = build_experiment_a_dataset(df_clean)
    assert len(res) == 1
    
    df_contaminated = pd.DataFrame([{"id": "1", "study_phase": "DRY_RUN"}, {"id": "2", "study_phase": "EXPERIMENT_A"}])
    failed_closed = False
    try:
        build_experiment_a_dataset(df_contaminated)
    except ValueError:
        failed_closed = True
    assert failed_closed is True
    print("Result: PASS (Experiment A dataset builder failed closed against DRY_RUN rows)")

if __name__ == "__main__":
    print("=== ZonePilot System Validation Suite ===")
    test_weather_leakage()
    test_scheduler_execution()
    test_backup_restore()
    test_dry_run_exclusion()
    print("\nAll system verification tests executed successfully.")
