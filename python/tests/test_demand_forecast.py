from onemove_intelligence.ml.demand_forecast import forecast_demand

def test_forecast_demand():
    df = forecast_demand()
    assert len(df) == 24
    assert "predicted_demand" in df.columns
    assert (df["predicted_demand"] >= 0).all()
