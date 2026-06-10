from onemove_intelligence.evaluation.model_evaluation import (
    evaluate_models,
    evaluate_forecast,
    evaluate_recommendations,
    evaluate_segments,
)


def test_evaluate_models_has_all_sections():
    report = evaluate_models()
    expected = {
        "forecast",
        "dispatch",
        "risk",
        "recommendations",
        "segments",
        "merchant_reliability",
        "partner_trust",
    }
    assert expected.issubset(report.keys())


def test_forecast_metrics_are_non_negative():
    metrics = evaluate_forecast()
    assert metrics["horizon_hours"] == 24
    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= metrics["mae"]  # RMSE >= MAE always holds
    assert metrics["mape_pct"] >= 0


def test_recommendation_coverage_is_a_percentage():
    metrics = evaluate_recommendations()
    assert 0 <= metrics["coverage_pct"] <= 100
    assert metrics["covered_customers"] <= metrics["customers"]


def test_segments_sum_to_population():
    segments = evaluate_segments()
    assert sum(segments.values()) == 201


def test_evaluation_is_deterministic():
    # Two runs must produce identical results (reproducibility guarantee).
    assert evaluate_models() == evaluate_models()
