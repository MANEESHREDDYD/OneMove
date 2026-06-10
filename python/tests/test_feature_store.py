from onemove_intelligence.features.feature_store import (
    FEATURE_REGISTRY,
    compute_feature_vector,
    features_for_model,
    get_feature,
    list_features,
)


def test_registry_is_non_empty_and_well_formed():
    assert len(FEATURE_REGISTRY) >= 5
    for name, defn in FEATURE_REGISTRY.items():
        assert defn.name == name
        assert defn.source_tables, f"{name} must declare source tables"
        assert defn.drift_risk in {"low", "medium", "high"}
        assert defn.served_to, f"{name} must declare at least one consumer"


def test_features_for_model_returns_known_features():
    feats = features_for_model("customer_segmentation")
    assert "customer_order_count_30d" in feats
    assert set(feats).issubset(set(list_features()))


def test_get_feature_unknown_raises():
    try:
        get_feature("does_not_exist")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_compute_feature_vector_training_serving_parity():
    orders = [
        {"customer_id": "c1", "status": "completed", "total_amount": 25.5},
        {"customer_id": "c1", "status": "cancelled", "total_amount": 10.0},
        {"customer_id": "c2", "status": "completed", "total_amount": 5.0},
    ]
    vec = compute_feature_vector(orders, "c1")
    assert vec["customer_order_count_30d"] == 1.0
    assert vec["customer_gmv_30d"] == 25.5
    assert vec["customer_cancel_rate"] == 0.5
    # Determinism: same inputs -> identical output vector.
    assert compute_feature_vector(orders, "c1") == vec
