# ZonePilot Architecture

## Operational Cloud Plane
The operational plane handles live data collection and volunteer interactions. It consists of the Observatory PWA (Next.js 16) hosted on Vercel, which communicates with a FastAPI backend hosted on Railway. Authentication uses Supabase invite-only Auth, and data lands in the Supabase Postgres `zonepilot` schema. Railway also runs cron collectors.

## Private Research Plane
This is an offline/local environment on the owner's laptop. It uses `zonepilot snapshot-pull` to download operational state into `$ZONEPILOT_DATA_ROOT/private/raw`, processes it through bronze/silver/gold Parquet layers, queries via DuckDB, and evaluates counterfactual policies via CP-SAT and digital twin simulations.

## Isolation
The Swiggy MCP Companion remains entirely physically and logically separate from the ZonePilot research modules.
