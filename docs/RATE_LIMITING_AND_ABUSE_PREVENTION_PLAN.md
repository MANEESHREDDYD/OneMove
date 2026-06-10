# Rate Limiting And Abuse Prevention Plan

Audit date: 2026-06-10

OneMove does not currently claim production-grade rate limiting. This document is the production-preview design plan.

## Local/Demo Current State

- Protected routes require authenticated Supabase sessions.
- RLS scopes role data at the database layer.
- Demo flows use deterministic data and demo accounts.
- No enforced production edge/API rate limiter is currently implemented.

## Required Production Controls

1. Edge rate limits for auth, checkout, ride booking, support ticket creation, and admin mutations.
2. Per-user and per-IP quotas.
3. Credential stuffing protection on login.
4. Bot and automation detection for high-risk flows.
5. Payment fraud throttles before any live payment integration.
6. Admin action audit logging and high-risk action throttles.
7. Webhook signature verification and replay protection.
8. Alerting on abnormal request volume, failed login bursts, and support spam.

## Preview Recommendation

For a preview deployment, add a conservative middleware/proxy rate limiter backed by a durable store before exposing the app outside a trusted private audience. Do not rely on in-memory counters for production.

