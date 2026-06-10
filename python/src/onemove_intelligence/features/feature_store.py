"""A lightweight, declarative feature store for OneMove Intelligence.

This module is the single source of truth for the features consumed by the
OneMove scoring models. It documents, in code, the definition / source table /
owner / freshness / drift risk of every feature, and provides a deterministic
``compute_feature_vector`` used by tests to guarantee training/serving parity.

The registry intentionally mirrors the real Supabase schema (``orders``,
``payments``, ``order_items``, ``order_status_events``, ``profiles``) so the
documentation in docs/FEATURE_STORE_DESIGN.md stays grounded in actual tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class FeatureDefinition:
    """Metadata describing one feature served to the OneMove models."""

    name: str
    description: str
    source_tables: List[str]
    dtype: str
    owner: str
    freshness: str          # how often the feature is recomputed
    drift_risk: str         # low | medium | high
    served_to: List[str]    # models / surfaces that consume this feature


# ---------------------------------------------------------------------------
# Feature registry — keep in sync with docs/FEATURE_STORE_DESIGN.md
# ---------------------------------------------------------------------------
FEATURE_REGISTRY: Dict[str, FeatureDefinition] = {
    "customer_order_count_30d": FeatureDefinition(
        name="customer_order_count_30d",
        description="Number of completed orders by a customer in the trailing 30 days.",
        source_tables=["orders"],
        dtype="int",
        owner="growth-analytics",
        freshness="hourly",
        drift_risk="medium",
        served_to=["customer_segmentation", "recommendations"],
    ),
    "customer_gmv_30d": FeatureDefinition(
        name="customer_gmv_30d",
        description="Total spend (GMV) by a customer in the trailing 30 days.",
        source_tables=["orders", "payments"],
        dtype="float",
        owner="growth-analytics",
        freshness="hourly",
        drift_risk="medium",
        served_to=["customer_segmentation"],
    ),
    "customer_cancel_rate": FeatureDefinition(
        name="customer_cancel_rate",
        description="Share of a customer's orders that ended in a cancelled status.",
        source_tables=["orders", "order_status_events"],
        dtype="float",
        owner="risk",
        freshness="hourly",
        drift_risk="high",
        served_to=["fraud_risk", "customer_segmentation"],
    ),
    "merchant_prep_time_mins": FeatureDefinition(
        name="merchant_prep_time_mins",
        description="Average order preparation time for a merchant.",
        source_tables=["orders", "order_status_events"],
        dtype="float",
        owner="marketplace-ops",
        freshness="hourly",
        drift_risk="medium",
        served_to=["merchant_reliability", "dispatch_optimizer"],
    ),
    "merchant_cancellation_rate": FeatureDefinition(
        name="merchant_cancellation_rate",
        description="Share of a merchant's orders that were cancelled.",
        source_tables=["orders"],
        dtype="float",
        owner="marketplace-ops",
        freshness="hourly",
        drift_risk="high",
        served_to=["merchant_reliability"],
    ),
    "partner_completion_rate": FeatureDefinition(
        name="partner_completion_rate",
        description="Share of assigned jobs a partner completed.",
        source_tables=["orders"],
        dtype="float",
        owner="supply-ops",
        freshness="hourly",
        drift_risk="medium",
        served_to=["partner_trust", "dispatch_optimizer"],
    ),
    "partner_avg_rating": FeatureDefinition(
        name="partner_avg_rating",
        description="Average customer rating of a partner (from job metadata).",
        source_tables=["orders"],
        dtype="float",
        owner="supply-ops",
        freshness="daily",
        drift_risk="low",
        served_to=["partner_trust"],
    ),
    "zone_demand_index": FeatureDefinition(
        name="zone_demand_index",
        description="Normalised demand level for a geographic zone and hour.",
        source_tables=["orders", "analytics_events"],
        dtype="float",
        owner="forecasting",
        freshness="hourly",
        drift_risk="high",
        served_to=["demand_forecast", "dispatch_optimizer"],
    ),
}


def list_features() -> List[str]:
    """Return all registered feature names (sorted, deterministic)."""
    return sorted(FEATURE_REGISTRY.keys())


def get_feature(name: str) -> FeatureDefinition:
    """Look up a single feature definition, raising a clear error if missing."""
    if name not in FEATURE_REGISTRY:
        raise KeyError(f"Unknown feature '{name}'. Known: {list_features()}")
    return FEATURE_REGISTRY[name]


def features_for_model(model: str) -> List[str]:
    """All feature names served to a given model/surface (training-serving parity)."""
    return sorted(
        name for name, defn in FEATURE_REGISTRY.items() if model in defn.served_to
    )


def compute_feature_vector(orders: List[dict], customer_id: str) -> Dict[str, float]:
    """Deterministically compute the customer feature vector from raw order rows.

    This is the *single* implementation used for both training and serving, which
    is how we guarantee training/serving consistency: the same function produces
    the vector offline (batch) and online (request time).
    """
    own = [o for o in orders if o.get("customer_id") == customer_id]
    completed = [o for o in own if o.get("status") in ("completed", "delivered")]
    cancelled = [o for o in own if o.get("status") == "cancelled"]
    gmv = sum(float(o.get("total_amount", 0) or 0) for o in completed)
    order_count = len(completed)
    cancel_rate = (len(cancelled) / len(own)) if own else 0.0

    return {
        "customer_order_count_30d": float(order_count),
        "customer_gmv_30d": round(float(gmv), 2),
        "customer_cancel_rate": round(float(cancel_rate), 4),
    }
