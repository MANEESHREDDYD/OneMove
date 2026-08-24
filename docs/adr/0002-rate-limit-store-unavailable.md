# ADR 0002 — Refuse rather than serve unmetered when the rate-limit store is down

**Status:** Accepted · **Date:** 2026-08-25

## Context

The distributed rate limiter is backed by PostgreSQL. When that store was
unreachable the middleware allowed READ-class requests through, logging
"degrading gracefully to allow low-risk read", and failed closed only for
writes, optimization, assistant and admin traffic.

That reasoning does not survive contact with the dependency graph. The rate
limit store is the *same* PostgreSQL instance the read routes query. Allowing
the request through did not serve the caller: it moved the failure a few frames
later, into the route, which returned an opaque `500 INTERNAL_ERROR`. Nothing
was served either way. The only difference was whether the caller could tell
what had happened and whether a retry was worth attempting.

It also left the system briefly unmetered at exactly the moment it was least
able to absorb load.

## Decision

Every limited endpoint class fails closed with `503 DEPENDENCY_UNAVAILABLE`,
`retryable: true`, a `Retry-After` header, and
`details.subsystem = "rate_limit_store"`.

Liveness, readiness and metrics endpoints are unaffected: they classify as
unlimited before this branch is reached, so a store outage cannot fail a probe,
trigger an instance-kill loop, or block the rollback that would fix it.

## Consequences

- A store outage is now a truthful, typed, retryable error rather than an
  opaque 500. Clients can back off instead of hammering a degraded system.
- There is no window in which traffic is served unmetered.
- Read availability is not reduced in practice, because the reads depended on
  the same store that is down.
- If the limiter is ever moved off PostgreSQL onto an independent store, this
  decision should be revisited: failing open for reads would then genuinely
  preserve availability, and would need its own ADR.

## Alternatives considered

**Keep failing open for reads.** Rejected: it served nothing, hid the cause
behind a 500, and removed the guard rail under load.

**Fail open for everything.** Rejected: unmetered traffic during a dependency
outage is how a degraded system becomes an unavailable one.
