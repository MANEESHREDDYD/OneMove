# 07 ZONEPILOT REUSE MATRIX

## Decision Paradigm
Reuse is desirable **only** where it does not contaminate the future ZonePilot experiment. Code that introduces synthetic simulation must be quarantined or replaced.

## Reusability Classifications

### 1. UI / Next.js Frontend Framework
**Classification**: `REUSE`
- The `app/`, `components/`, and Next.js scaffolding are cleanly constructed and visually polished. They can be reused as the surface-level presentation layer for ZonePilot.

### 2. Database Schema (Supabase)
**Classification**: `REUSE_WITH_MODIFICATION`
- The tables exist, but lack indexes (P1).
- The RLS policies are highly insecure and must be rewritten from scratch (P0).

### 3. Dispatch Logic (C Engine & TS Utils)
**Classification**: `REPLACE`
- The current engines perform static Haversine nearest-neighbor lookups or hardcoded distance hashes (`simpleHash`). This must be replaced with an actual optimization engine.

### 4. Intelligence & ML (Python)
**Classification**: `QUARANTINE / REPLACE`
- The Python models generate seeded sine waves instead of statistical predictions. They must be quarantined to prevent contaminating the ZonePilot datasets.

### 5. Data Generators (`scripts/`)
**Classification**: `QUARANTINE`
- The faker seed scripts cannot be used for live experimental training data. They may only be used to populate the initial baseline map structure.
