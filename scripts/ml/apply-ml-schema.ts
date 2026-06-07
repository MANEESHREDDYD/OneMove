import { Client } from 'pg'
import dotenv from 'dotenv'
import fs from 'fs'

dotenv.config({ path: '.env.local' })

const sql = `
CREATE TABLE IF NOT EXISTS public.demand_forecasts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    zone_id TEXT NOT NULL,
    forecast_timestamp TIMESTAMPTZ NOT NULL,
    predicted_demand_level TEXT NOT NULL CHECK (predicted_demand_level IN ('LOW', 'MEDIUM', 'HIGH', 'SURGE')),
    expected_order_volume INTEGER NOT NULL,
    confidence_score NUMERIC NOT NULL,
    factors TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.risk_checks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    risk_score NUMERIC NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    factors TEXT[] DEFAULT '{}',
    action_taken TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.demand_forecasts DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.risk_checks DISABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS public.recommendations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_id UUID NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    score NUMERIC NOT NULL,
    confidence NUMERIC NOT NULL,
    reasoning TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.customer_segments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_id UUID NOT NULL,
    segment_name TEXT NOT NULL,
    feature_values JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.merchant_reliability_scores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    merchant_id UUID NOT NULL,
    reliability_score NUMERIC NOT NULL,
    risk_level TEXT NOT NULL,
    factors TEXT[] DEFAULT '{}',
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.partner_trust_scores (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    partner_id UUID NOT NULL,
    trust_score NUMERIC NOT NULL,
    status TEXT NOT NULL,
    factors TEXT[] DEFAULT '{}',
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.recommendations DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_segments DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.merchant_reliability_scores DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.partner_trust_scores DISABLE ROW LEVEL SECURITY;
`

async function main() {
  const client = new Client({ connectionString: process.env.DIRECT_URL })
  await client.connect()
  await client.query(sql)
  console.log('Migration applied successfully')
  process.exit(0)
}

main().catch(err => {
  console.error(err)
  process.exit(1)
})
