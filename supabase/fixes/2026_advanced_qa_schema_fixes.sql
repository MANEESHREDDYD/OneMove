-- 2026_advanced_qa_schema_fixes.sql

alter table public.orders add column if not exists metadata jsonb not null default '{}'::jsonb;
alter table public.orders add column if not exists idempotency_key text;

alter table public.payments add column if not exists idempotency_key text;
alter table public.order_status_events add column if not exists idempotency_key text;
alter table public.analytics_events add column if not exists idempotency_key text;

create unique index if not exists idx_orders_idempotency_key on public.orders(idempotency_key) where idempotency_key is not null;
create unique index if not exists idx_payments_idempotency_key on public.payments(idempotency_key) where idempotency_key is not null;
create unique index if not exists idx_order_status_events_idempotency_key on public.order_status_events(idempotency_key) where idempotency_key is not null;
create unique index if not exists idx_analytics_events_idempotency_key on public.analytics_events(idempotency_key) where idempotency_key is not null;

create index if not exists idx_orders_service_type on public.orders(service_type);
create index if not exists idx_orders_status on public.orders(status);
create index if not exists idx_orders_customer_id on public.orders(customer_id);
create index if not exists idx_orders_merchant_id on public.orders(merchant_id);
create index if not exists idx_orders_driver_id on public.orders(driver_id);
create index if not exists idx_orders_created_at on public.orders(created_at);
create index if not exists idx_orders_service_status_created_at on public.orders(service_type, status, created_at desc);
