-- Performance Optimizations: Database Indexes

-- Profiles
CREATE INDEX IF NOT EXISTS idx_profiles_role ON profiles(role);
CREATE INDEX IF NOT EXISTS idx_profiles_is_demo ON profiles(is_demo);

-- Merchants
CREATE INDEX IF NOT EXISTS idx_merchants_category ON merchants(category);
CREATE INDEX IF NOT EXISTS idx_merchants_status ON merchants(status);
CREATE INDEX IF NOT EXISTS idx_merchants_owner_id ON merchants(owner_id);

-- Products
CREATE INDEX IF NOT EXISTS idx_products_merchant_id ON products(merchant_id);

-- Orders
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_merchant_id ON orders(merchant_id);
CREATE INDEX IF NOT EXISTS idx_orders_driver_id ON orders(driver_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_orders_service_type ON orders(service_type);

-- Order Items
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- Payments
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_customer_id ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);

-- Tracking
CREATE INDEX IF NOT EXISTS idx_tracking_is_online ON tracking(is_online);

-- Support Tickets
CREATE INDEX IF NOT EXISTS idx_support_tickets_customer_id ON support_tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);

-- Ratings Reviews
CREATE INDEX IF NOT EXISTS idx_ratings_reviews_target_id ON ratings_reviews(target_id);

-- Analytics Events
CREATE INDEX IF NOT EXISTS idx_analytics_events_created_at ON analytics_events(created_at);
CREATE INDEX IF NOT EXISTS idx_analytics_events_event_type ON analytics_events(event_type);

-- ML Score Logs
CREATE INDEX IF NOT EXISTS idx_ml_score_logs_target_id ON ml_score_logs(target_id);
CREATE INDEX IF NOT EXISTS idx_ml_score_logs_score_type ON ml_score_logs(score_type);

-- Order Status Events
CREATE INDEX IF NOT EXISTS idx_order_status_events_order_id ON order_status_events(order_id);
