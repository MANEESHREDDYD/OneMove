# Data Lineage Manifest

## Flow
1. **Raw to Fact:** `orders` & `payments` -> `fact_orders`
2. **Fact to Mart:** `fact_orders` -> `mart_daily_marketplace_metrics` -> **Admin Analytics Dashboard**
3. **Raw to Features:** `orders` & `status_events` -> `feature_store`
4. **Features to Scores:** `feature_store` -> `ml_pipeline` -> **Admin Intelligence Pages**

## Architecture
This lineage guarantees that the ML models and Analytics Dashboards operate on a Single Source of Truth (SSOT).
