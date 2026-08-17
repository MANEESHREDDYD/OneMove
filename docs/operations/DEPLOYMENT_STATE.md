# Deployment state

**Reference commit:** `main` at `666ade66f965df76097c557cdf419501b683db75`.

What is actually deployed, what is only provisioned, and what is not wired. This document exists
because "we have a Vercel project / a Supabase project / a Sentry org" is repeatedly mistaken for
"it is deployed and it works". Three of the four rows below are the former.

## Summary

| Component | State | Reality |
| --- | --- | --- |
| Observatory frontend (`apps/observatory`) | **DEPLOYED** | Live at <https://zonepilot-observatory.vercel.app> |
| ZonePilot API (`services/api`) | **NOT DEPLOYED** | No host. No usable Railway token. |
| Supabase (`puygqvnhwsjkspoprfkb`) | **PROVISIONED ONLY** | `ACTIVE_HEALTHY`, JWKS serving `ES256`; not integrated into any running ZonePilot deployment |
| Sentry (org `onemove`) | **PROVISIONED, NOT INSTRUMENTED** | Test event proven received; the Observatory sends nothing |
| Evidence artifacts | **EPHEMERAL** | GitHub Actions artifacts, 30-day retention. No durable object store. |

## 1. Observatory frontend — deployed

| Property | Value |
| --- | --- |
| URL | <https://zonepilot-observatory.vercel.app> |
| `<title>` | `ZonePilot Observatory` |
| Deployed commit | `666ade66f965df76097c557cdf419501b683db75` |
| Vercel deployment | `dpl_CKsnEo7tfPu9gV2Jt3ZNS9VqkkZj` |
| GitHub Deployment record | `5941546097`, environment `production`, created `2026-08-17T08:28:34Z` |

All four routes answer `200`:

| Route | Purpose |
| --- | --- |
| `/` | Network map |
| `/capture` | Field capture |
| `/qc` | Quality control |
| `/system-health` | Release identity + provider health surface |

### It has no API to call

**No ZonePilot backend is deployed anywhere.** The Observatory proxies `/api/zonepilot/[...path]` to
`process.env.ZONEPILOT_API_URL`, which **defaults to `http://127.0.0.1:8000`** — a loopback address
that means nothing on Vercel. There is no such API running. The deployed site is a shell that renders
its own unavailable states. In particular `/system-health` consumes `GET /api/v1/version` and
`GET /api/v1/data-health`, and with no backend it can only report both as unavailable. Nobody has
ever seen that page display a verified release identity.

This is the single most important fact about the deployment: **the live URL is a frontend, not a
running product.**

### Vercel is not connected to GitHub

There is **no GitHub integration on the Vercel project**. Consequences, all of them operational
hazards rather than theoretical ones:

- **No push-to-deploy.** Merging to `main` changes nothing in production.
- **Every deploy is a manual upload** from a workstation.
- **No preview deployments per pull request.**
- **The GitHub Deployment record is written by hand after the fact.** Deployment `5941546097` asserts
  that the bundle came from `666ade66`; nothing verifies that assertion. The commit-to-bundle link is
  a claim, not a proof.
- **Production silently drifts.** The next merge to `main` leaves the deployed bundle behind with no
  signal anywhere that it happened.

Do not describe this project as having continuous deployment.

## 2. ZonePilot API — not deployed

The FastAPI app (`services.api.main:app`) runs only locally. Railway is the intended host per
[`docs/system/DEPLOYMENT_TOPOLOGY.md`](../system/DEPLOYMENT_TOPOLOGY.md), but **there is no usable
Railway token**, so no deployment has been attempted.

Downstream consequences:

- The release gate `GET /api/v1/version` — see [`RELEASE_IDENTITY.md`](RELEASE_IDENTITY.md) — has
  never run against a real deployment. Its required configuration (`ZONEPILOT_APP_VERSION`,
  `ZONEPILOT_GIT_SHA`, `ZONEPILOT_SCHEMA_VERSION`, `ZONEPILOT_DATA_ROOT`) has never been set on a
  deployment platform.
- The mounted artifact root that every working `/api/v1` route depends on does not exist in any hosted
  environment. Even if the API were deployed as-is, every Observatory route would return
  `503 DATASET_NOT_READY`.
- The rate limiter is in-process and has never been exercised under real traffic.
- No production security configuration has ever been reviewed, because none exists.

## 3. Supabase — provisioned, not integrated

| Property | Value |
| --- | --- |
| Project ref | `puygqvnhwsjkspoprfkb` |
| Status | `ACTIVE_HEALTHY` |
| Region | `ap-southeast-1` |
| JWKS | serving `ES256` |

The project exists and its JWKS endpoint is reachable, which is what the API's asymmetric verification
path expects. But no deployed ZonePilot process points at it. JWT verification against this project
has been exercised only by the local test suite, never by a hosted API handling a real session.

`workspace_id` exists in **no merged migration**, so this project cannot issue the workspace claim the
API's multi-tenant check looks for. See [`../SECURITY.md`](../SECURITY.md).

## 4. Sentry — provisioned, and the Observatory sends nothing

A Sentry org (`onemove`) exists and a **test event was proven received**, so the account and DSN work.

**The Observatory has zero Sentry instrumentation.** State it plainly:

- `apps/observatory/package.json` has **no `@sentry/nextjs` dependency**.
- There is no `sentry.client.config.*`, `sentry.server.config.*`, `sentry.edge.config.*`, or
  `instrumentation.ts` in `apps/observatory`.
- **Nothing in `apps/observatory` reads a Sentry DSN.**

Therefore **no real frontend error will ever reach Sentry.** A user hitting a crash on the live site
produces no alert, no issue, and no trace. The only Sentry integration in the repository is the
FastAPI path in `services/api/core/telemetry.py`, gated on `SENTRY_DSN` — and that application is not
deployed. Net effect: **there is no error monitoring on anything that is actually running.**

A received test event proves the DSN is valid. It does not prove the product is instrumented, and it
must never be cited as if it did.

## 5. Evidence durability

R1 evidence manifests are uploaded as **GitHub Actions artifacts with 30-day retention**. There is no
durable object store, no signed attestation, and no archive. Evidence for a commit older than 30 days
is gone unless it is regenerated by re-running the pipeline. See
[`../EVIDENCE_MODEL.md`](../EVIDENCE_MODEL.md).

## 6. What would have to change

Ordered by how much dishonesty each one removes, not by effort:

1. **Deploy the API somewhere** and set the four release-identity variables from the built artifact,
   so `GET /api/v1/version` can return `200` against something real.
2. **Mount an artifact root** in that environment, so the Observatory routes serve verified Gold/OSRM
   data instead of `503 DATASET_NOT_READY`.
3. **Connect Vercel to GitHub**, so the deployed bundle is provably a commit rather than an assertion.
4. **Add `@sentry/nextjs` to the Observatory**, so a frontend crash produces a signal.
5. **Move evidence to durable storage** with an attestation, so a manifest outlives its 30-day window.

Until at least (1) and (2) land, "ZonePilot is deployed" is false; the accurate statement is
"the ZonePilot Observatory frontend is deployed and has no backend."
