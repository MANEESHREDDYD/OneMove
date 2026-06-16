from dataclasses import dataclass

@dataclass
class FeatureDef:
    name: str
    source_tables: list
    drift_risk: str
    served_to: list

FEATURE_REGISTRY = {
    "customer_order_count_30d": FeatureDef("customer_order_count_30d", ["orders"], "low", ["customer_segmentation"]),
    "customer_gmv_30d": FeatureDef("customer_gmv_30d", ["orders"], "medium", ["customer_segmentation"]),
    "customer_cancel_rate": FeatureDef("customer_cancel_rate", ["orders"], "medium", ["risk"]),
    "partner_acceptance_rate": FeatureDef("partner_acceptance_rate", ["dispatch"], "high", ["dispatch"]),
    "zone_demand_index": FeatureDef("zone_demand_index", ["demand"], "high", ["pricing"]),
}

def list_features():
    return list(FEATURE_REGISTRY.keys())

def get_feature(name):
    if name not in FEATURE_REGISTRY:
        raise KeyError(f"Feature {name} not found")
    return FEATURE_REGISTRY[name]

def features_for_model(model_name):
    return [name for name, f in FEATURE_REGISTRY.items() if model_name in f.served_to]

def compute_feature_vector(orders, customer_id):
    customer_orders = [o for o in orders if o["customer_id"] == customer_id]
    completed = [o for o in customer_orders if o["status"] == "completed"]
    cancelled = [o for o in customer_orders if o["status"] == "cancelled"]
    
    count = len(completed)
    gmv = sum(o["total_amount"] for o in completed)
    cancel_rate = len(cancelled) / len(customer_orders) if customer_orders else 0.0
    
    return {
        "customer_order_count_30d": float(count),
        "customer_gmv_30d": float(gmv),
        "customer_cancel_rate": float(cancel_rate),
    }

def get_customer_features(customer_id: str):
    return {
        "lifetime_rides": 42,
        "average_order_value": 25.50,
        "days_since_last_order": 2,
        "fraud_risk_score": 0.05
    }
