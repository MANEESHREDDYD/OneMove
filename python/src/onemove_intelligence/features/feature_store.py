def get_customer_features(customer_id: str):
    """Retrieves real-time and batch features for a given customer."""
    print(f"Retrieving features for {customer_id}...")
    return {
        "lifetime_rides": 42,
        "average_order_value": 25.50,
        "days_since_last_order": 2,
        "fraud_risk_score": 0.05
    }
