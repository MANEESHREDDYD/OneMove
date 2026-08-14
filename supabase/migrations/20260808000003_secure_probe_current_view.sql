-- 20260808000003_secure_probe_current_view.sql
-- Enforce security_invoker = true on probe_observations_current view so caller RLS policies apply strictly

CREATE OR REPLACE VIEW public.probe_observations_current WITH (security_invoker = true) AS
SELECT p.* 
FROM public.probe_observations p
WHERE NOT EXISTS (
    SELECT 1 FROM public.probe_observations c 
    WHERE c.supersedes_id = p.id 
      AND c.record_status = 'ACTIVE'
) AND p.record_status = 'ACTIVE';
