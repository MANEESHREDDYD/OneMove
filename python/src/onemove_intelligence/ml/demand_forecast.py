import pandas as pd
import numpy as np

def forecast_demand():
    """Deterministic demand forecasting using historical patterns."""
    print("Forecasting demand for upcoming 24 hours...")
    # Simulated deterministic logic
    np.random.seed(42)
    hours = pd.date_range(start="2026-06-10", periods=24, freq="h")
    base_demand = np.sin(np.linspace(0, 3.14 * 2, 24)) * 50 + 100
    noise = np.random.normal(0, 5, 24)
    demand = np.maximum(0, base_demand + noise).astype(int)
    
    forecast_df = pd.DataFrame({
        "timestamp": hours,
        "predicted_demand": demand
    })
    
    print(f"Generated forecast for {len(forecast_df)} hours.")
    return forecast_df
