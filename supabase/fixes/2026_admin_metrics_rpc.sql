-- 2026_admin_metrics_rpc.sql

CREATE OR REPLACE FUNCTION public.get_admin_dashboard_metrics()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  result jsonb;
  total_orders bigint;
  total_revenue numeric;
  active_drivers bigint;
  active_merchants bigint;
  orders_by_status jsonb;
  orders_by_service jsonb;
  recent_events_count bigint;
BEGIN
  IF NOT public.is_admin() THEN
    RAISE EXCEPTION 'Access denied';
  END IF;

  SELECT count(*), COALESCE(sum(total_amount), 0)
  INTO total_orders, total_revenue
  FROM public.orders;

  SELECT count(*) INTO active_drivers
  FROM public.profiles WHERE role = 'driver';

  SELECT count(*) INTO active_merchants
  FROM public.merchants WHERE status = 'active';

  SELECT json_object_agg(status, count)
  INTO orders_by_status
  FROM (SELECT status, count(*) FROM public.orders GROUP BY status) t;

  SELECT json_object_agg(service_type, count)
  INTO orders_by_service
  FROM (SELECT service_type, count(*) FROM public.orders GROUP BY service_type) t;

  SELECT count(*) INTO recent_events_count
  FROM public.order_status_events
  WHERE created_at > now() - interval '24 hours';

  result := jsonb_build_object(
    'total_orders', total_orders,
    'total_revenue', total_revenue,
    'active_drivers', active_drivers,
    'active_merchants', active_merchants,
    'orders_by_status', COALESCE(orders_by_status, '{}'::jsonb),
    'orders_by_service', COALESCE(orders_by_service, '{}'::jsonb),
    'recent_events_count', recent_events_count
  );

  RETURN result;
END;
$$;
