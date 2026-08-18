import pandas as pd
import pytest

from services.collectors.openmeteo_real import select_point_in_time_forecast
from services.etl.pipeline import build_experiment_a_dataset


def test_point_in_time_weather_leakage_gate():
    prediction_time = pd.Timestamp("2026-08-08 18:00:00+05:30")
    valid_time = pd.Timestamp("2026-08-08 19:00:00+05:30")

    # Forecast A: issued 17:30 IST, valid 19:00 IST (Eligible!)
    # Forecast B: issued 18:05 IST, valid 19:00 IST (Future leakage - MUST BE REJECTED!)
    forecasts = pd.DataFrame(
        [
            {
                "id": "forecast_A",
                "issued_at": pd.Timestamp("2026-08-08 17:30:00+05:30"),
                "valid_at": valid_time,
                "temp": 24.5,
            },
            {
                "id": "forecast_B",
                "issued_at": pd.Timestamp("2026-08-08 18:05:00+05:30"),
                "valid_at": valid_time,
                "temp": 28.0,
            },
        ]
    )

    selected = select_point_in_time_forecast(forecasts, prediction_time, valid_time)
    assert selected is not None, "Failed to select eligible forecast A"
    assert selected["id"] == "forecast_A", (
        f"Leakage violation! Selected {selected['id']} issued in future instead of forecast_A"
    )
    assert selected["temp"] == 24.5


def test_dry_run_exclusion_experiment_a():
    df_clean = pd.DataFrame([{"id": "1", "study_phase": "EXPERIMENT_A"}])
    res = build_experiment_a_dataset(df_clean)
    assert len(res) == 1

    df_contaminated = pd.DataFrame([{"id": "1", "study_phase": "DRY_RUN"}, {"id": "2", "study_phase": "EXPERIMENT_A"}])
    with pytest.raises(ValueError) as exc:
        build_experiment_a_dataset(df_contaminated)
    assert "DRY_RUN rows in dataset" in str(exc.value)
