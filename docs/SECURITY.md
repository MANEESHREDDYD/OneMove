# ZonePilot Security

**Scope:** the ZonePilot API (`services/api/`) and the public/private repository boundary.
**Reference commit:** `main` at `502e20817d4319d6867090b7765fe35326973e67`.

This document states what is implemented and what is not. The gaps in section 7 are real and are not
softened.

> This is an engineering reference, not a vulnerability disclosure policy. ZonePilot is **not
> deployed anywhere**, so there is no production attack surface today.

---

## 1. Authentication model

All ZonePilot read routes under `/api/v1` require a **Supabase-issued JWT** presented as
`Authorization: Bearer <token>`. Verification lives in `services/api/core/auth.py`.

There is **no mock JWT path, no development bypass, and no fallback signing secret.** If the verifier
is not configured, requests fail with `500` rather than succeeding unverified.

### Verification steps

1. `HTTPBearer(auto_error=False)` extracts the credential; a missing credential is `401 Not authenticated`.
2. The **unverified header** is read only to learn the `alg`.
3. `alg` is checked against the allowlist **twice**: against the configured allowlist and against the
   hardcoded set `{ES256, RS256, HS256}`. Anything else raises `InvalidAlgorithmError`.
4. The **verification key is selected by algorithm**, not by the token:
   - `HS256` -> `SUPABASE_JWT_SECRET` only
   - `ES256` / `RS256` -> `SUPABASE_JWT_PUBLIC_KEY`, else the JWKS endpoint
5. `jwt.decode()` runs with `algorithms=[alg]` (single element — the exact algorithm), the expected
   **audience** (`SUPABASE_JWT_AUDIENCE`, default `authenticated`), and the expected **issuer** when
   one is resolvable.
6. A token without `sub` is rejected.

### Issuer resolution

`SUPABASE_JWT_ISSUER` if set (trailing slash stripped), otherwise derived as
`{SUPABASE_URL}/auth/v1`. If neither is available, the issuer claim is not checked — **configure
`SUPABASE_URL` or `SUPABASE_JWT_ISSUER` in any real deployment.**

### JWKS

`jwt.PyJWKClient` with `cache_keys=True`, `cache_jwk_set=True`, `lifespan=600`, `timeout=5`, memoized
per URL via `lru_cache`. The URL is `SUPABASE_JWKS_URL` or
`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`.

Failure handling distinguishes availability from validity:

| Condition | Response |
| --- | --- |
| `PyJWKClientConnectionError` (JWKS unreachable) | `503 Token verification temporarily unavailable` |
| `PyJWKClientError` (no matching key) | `401 Invalid token` |
| JWKS/public key not configured for an asymmetric token | `500 Supabase JWKS verifier is not configured` |

An unreachable identity provider therefore **fails closed** and is never mistaken for a valid token.

### Error mapping

| Failure | Response |
| --- | --- |
| Expired | `401 Token expired` |
| Wrong issuer | `401 Invalid token: wrong issuer` |
| Wrong audience | `401 Invalid token: wrong audience` |
| Any other invalid token | `401 Invalid token` |

---

## 2. Algorithm-confusion mitigation

The classic JWT algorithm-confusion attack is: take a token signed with an asymmetric key, flip the
header to `HS256`, and sign it with the server's **public key** as if it were an HMAC secret — because
the server passed a single "key" variable into a verifier that accepted multiple algorithms.

The `HS256` entry in the default allowlist exists for a genuine reason: during a Supabase signing-key
migration, a project issues new asymmetric tokens while legacy sessions remain `HS256`. Both must
verify. The mitigation is that **key material is never shared across algorithm families**:

```python
def _verification_key(token: str, algorithm: str):
    if algorithm == "HS256":
        secret = os.environ.get("SUPABASE_JWT_SECRET")   # symmetric secret ONLY
        ...
        return secret
    public_key = os.environ.get("SUPABASE_JWT_PUBLIC_KEY")   # asymmetric ONLY
    ...
```

Three properties make the confusion path unreachable:

1. **Independent key source.** An `HS256` token is only ever verified against `SUPABASE_JWT_SECRET`.
   It can never be verified against a public key, so a public key cannot be used as an HMAC secret.
2. **Single-algorithm decode.** `algorithms=[algorithm]` is passed with exactly one element, so PyJWT
   cannot fall back to a different algorithm than the one whose key was selected.
3. **Double allowlist check.** The header algorithm must satisfy both the configurable allowlist and
   the hardcoded `{ES256, RS256, HS256}` set, so `none` and every other algorithm are rejected before
   key selection.

**Hardening for deployments not mid-migration:** set `SUPABASE_JWT_ALGORITHMS=ES256,RS256` to drop
`HS256` entirely, and leave `SUPABASE_JWT_SECRET` unset.

Covered by `tests/api/test_jwt_security.py`, plus `tests/api/test_auth.py`,
`tests/api/test_role_attacks.py`, and `tests/api/test_rls_execution.py`.

---

## 3. Rate limiting

Implemented in `RequestIdMiddleware` (`services/api/core/middleware.py`) using `rate_limiter` and
`rate_policy` from `services/api/core/telemetry.py`. Applied **before** routing and before body
handling.

| Bucket | Matches | Default limit/min | Env override |
| --- | --- | --- | --- |
| `auth` | path contains `/auth` | 10 | `ZONEPILOT_AUTH_RATE_LIMIT_PER_MINUTE` |
| `expensive` | path contains `/scenarios`, `/optimizer`, or `/jobs` | 20 | `ZONEPILOT_EXPENSIVE_RATE_LIMIT_PER_MINUTE` |
| `authenticated` | any authenticated request | 120 | `ZONEPILOT_API_RATE_LIMIT_PER_MINUTE` |

Enabled by default (`ZONEPILOT_RATE_LIMIT_ENABLED`).

**Principal identity is opaque.** The bearer token (or the client IP for unauthenticated requests) is
hashed with `opaque_principal()` — SHA-256, first 24 hex chars — so no credential material reaches
the limiter's key space or any log line.

A limited request returns `429` with the standard envelope, `retry-after`, and
`details.{bucket, limit_per_minute}`.

**Limitation:** the limiter is **in-process**. Multiple API replicas would each enforce their own
counters, so the effective limit multiplies by the replica count. Not an issue today (nothing is
deployed), but it must be replaced with a shared store before horizontal scaling.

**Note:** unauthenticated requests to non-`/auth` paths match **no bucket** and are therefore
unlimited by this middleware.

---

## 4. Request handling and the error envelope

### Request/correlation IDs

`x-request-id` and `x-correlation-id` are accepted from the client but **validated before use**:
`safe_request_id()` requires `^[A-Za-z0-9._:-]{1,128}$` and otherwise substitutes a fresh UUID4. This
prevents log injection and unbounded header values. Both IDs are echoed on every response.

### Payload limits

`content-length` is parsed and validated. A non-integer or negative value is `400
INVALID_CONTENT_LENGTH`; anything over **4 MiB** is `413 PAYLOAD_TOO_LARGE`.

### Error envelope

Every failure path — `HTTPException`, `RequestValidationError`, rate limit, payload limit, and
unhandled `500` — returns the same shape:

```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human readable message",
    "request_id": "...",
    "retryable": false,
    "details": {}
  }
}
```

`retryable` is true for `408`, `429`, `500`, `502`, `503`, `504`.

Codes in use: `UNAUTHORIZED`, `FORBIDDEN`, `VALIDATION_ERROR`, `RATE_LIMITED`,
`INVALID_CONTENT_LENGTH`, `PAYLOAD_TOO_LARGE`, `INTERNAL_SERVER_ERROR`, `NOT_IMPLEMENTED`,
`NOT_FOUND`, `INVALID_ARGUMENT`, `DATASET_NOT_READY`, `ARTIFACT_INTEGRITY_ERROR`.

**Unhandled exceptions never leak internals.** The middleware catches them, logs the full traceback
server-side, optionally reports to Sentry, and returns a fixed `"An unexpected error occurred."`.
Validation errors are projected into a safe `{location, type, message}` list rather than echoing
PyDantic's raw error objects (which can contain submitted input).

### Logging

`JsonFormatter` emits structured JSON and **redacts** any field named `authorization`, `password`,
`token`, `jwt`, `api_key`, `apikey`, `refresh_token`, or `secret`. Exceptions are logged as
`exception_type` only. Sentry is initialised with `send_default_pii=False`.

### CORS

Origins come from `ZONEPILOT_ALLOWED_ORIGINS` (default: localhost `:3000`/`:3001`). Headers are
restricted to `authorization`, `content-type`, `x-correlation-id`, `x-request-id`, `x-workspace-id`.
`allow_credentials=True`, so **the origin list must never contain a wildcard.**

### Operational endpoints

| Endpoint | Auth | Notes |
| --- | --- | --- |
| `/healthz` | none | Liveness only; returns no internal state |
| `/readyz` | none | Attempts `SELECT 1` against `ZONEPILOT_DB_URL` (3 s timeout); `503` when unready. Returns only `{status, db_connected}` — no error detail |
| `/metrics` | token | **Disabled by default.** `404` unless `ZONEPILOT_METRICS_ENABLED` is truthy; then requires `Bearer $ZONEPILOT_METRICS_TOKEN`, compared with `hmac.compare_digest` |

`/metrics` returning `404` rather than `403` when disabled avoids confirming the endpoint exists.

**Gap:** if `ZONEPILOT_METRICS_ENABLED` is on but `ZONEPILOT_METRICS_TOKEN` is unset, the token check
is skipped and metrics are exposed unauthenticated. Always set both together.

---

## 5. Artifact access

`ArtifactCatalogRepository` (`services/api/repositories/artifact_catalog.py`) is **read-only** and
resolves every path against a configured root, raising `ArtifactCatalogError` if the resolved path
escapes it — a path-traversal guard for the `{entity_type}/{entity_id}` and layer-name inputs.

Artifacts are re-hashed on read; a mismatch is `409 ARTIFACT_INTEGRITY_ERROR`. Missing manifests fail
closed with `503 DATASET_NOT_READY` rather than returning empty or synthetic data.

---

## 6. Public/private repository boundary

`MANEESHREDDYD/OneMove` is a **public** repository. The boundary is enforced by construction:

- **Raw and derived data never enter git.** `.gitignore` excludes `data/`, `data_root/`,
  `data_root/private/`, `artifacts/`, `scratch/`, `*.parquet`, `*.pbf`, `*.osm`, plus assorted local
  run logs.
- **All private artifacts live under `.../private/official/`**, a path that is git-ignored by two
  separate rules.
- **Only a sanitized projection is published.** `services/evidence/r1.py` emits hashes, counts,
  versions, and DQ status — never data rows, never geometry.
- **Secrets are never committed.** `.env*`, `private/`, and credential exports are ignored;
  GitHub secret scanning reports **0 alerts** at `502e2081`.
- **Container images are pinned by digest**, not tag (`osmium` and OSRM), and CI actions are pinned by
  commit SHA — so a mutated upstream tag cannot silently change what CI executes.
- `make public-export` / `make publish-check` (`services/etl/public_export.py`,
  `services/etl/publish_check.py`) exist as an explicit export/validation gate for anything intended
  to become public.

### Static analysis

CodeQL runs on push and pull request against `main` with a pinned action. At `502e2081`: **0 open
CodeQL alerts, 0 secret-scanning alerts, 2 medium Dependabot alerts.**

---

## 7. Known gaps

These are real weaknesses in the current implementation.

### 7.1 Role checks are inert

`get_current_user()` contains role enforcement:

```python
token_role = payload.get("role", "anon")
req_role = getattr(request.state, "required_role", None)
if req_role and token_role != req_role:
    raise HTTPException(status_code=403, detail="Invalid token: wrong role")
```

But `request.state.required_role` is **never set anywhere in application code**. The only assignment
in the repository is in a test:

```
services/api/core/auth.py:133   req_role = getattr(request.state, "required_role", None)
tests/api/test_jwt_security.py:131   request.state.required_role = "admin"
```

**Consequence:** `req_role` is always `None` at runtime, the comparison short-circuits, and **no route
enforces any role.** Every authenticated caller has identical access to every `/api/v1` route. The
mechanism is present and tested in isolation, but it is not wired to a single endpoint. There is no
route-level RBAC.

### 7.2 Multi-tenant isolation is not enforceable

`get_current_user()` also contains a workspace check:

```python
req_workspace = request.headers.get("x-workspace-id")
token_workspace = payload.get("workspace_id")
if req_workspace and token_workspace and req_workspace != token_workspace:
    raise HTTPException(status_code=403, detail="Invalid token: wrong workspace")
```

**`workspace_id` exists in no migration.** There is no `workspace_id` column in any SQL file under
`supabase/`. Therefore:

- no Supabase JWT will ever carry a `workspace_id` claim,
- `token_workspace` is always `None`,
- the check short-circuits and **never fires**,
- and even if it did fire, it compares a client-supplied header to a claim, which is a consistency
  check — **not** a data-scoping mechanism.

**Consequence: multi-tenant isolation is not enforceable at the API layer.** No query is scoped by
workspace, no row is tagged with a workspace, and the `x-workspace-id` header is accepted by CORS but
is semantically inert. ZonePilot is currently a **single-tenant** system and must not be described
otherwise.

### 7.3 The `governance` router has no authentication

`services/api/routers/governance.py` exposes four routes under `/governance` —
`POST /consent`, `POST /withdraw`, `POST /activate`, `GET /retention` — with **no `Depends(...)` auth
dependency of any kind**. They currently return hardcoded strings and touch no storage, so nothing is
exposed or mutated today, but they are unauthenticated endpoints with governance-suggestive names and
must be secured before they do anything real.

### 7.4 Other gaps

| Gap | Notes |
| --- | --- |
| **Rate limiter is in-process** | Limits multiply by replica count under horizontal scaling |
| **Unauthenticated non-`/auth` paths are not rate limited** | `rate_policy()` returns `None` for them |
| **Issuer check is skipped when unresolvable** | Deploying without `SUPABASE_URL`/`SUPABASE_JWT_ISSUER` disables issuer validation |
| **`/metrics` token check is skipped if the token is unset** | Set `ZONEPILOT_METRICS_ENABLED` and `ZONEPILOT_METRICS_TOKEN` together |
| **`HS256` in the default allowlist** | Safe by key separation, but narrow it with `SUPABASE_JWT_ALGORITHMS=ES256,RS256` when not mid-migration |
| **No signed evidence attestation** | Manifest integrity relies on trusting the CI run |
| **Evidence classes have no database constraint** | See [`EVIDENCE_MODEL.md`](EVIDENCE_MODEL.md) |
| **Legacy `/v1/events` and `/v1/probes`** | Belong to the earlier field-study design; `/v1/probes` re-parses the `Authorization` header manually rather than using the dependency, and uses a service-role Supabase client that bypasses RLS for assignment lookups and idempotency checks |
| **2 medium Dependabot alerts open** | At `502e2081` |
| **Nothing is deployed** | There is no production configuration to review, and none of the above has been validated under real traffic |
