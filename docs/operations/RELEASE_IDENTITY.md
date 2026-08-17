# Release identity contract

`GET /api/v1/version` is an authenticated release gate, not a best-effort metadata endpoint. It returns HTTP 200 only when one deployed application identity is tied to verified Gold and OSRM graph artifacts.

## Required deployment configuration

The API process requires:

- `ZONEPILOT_APP_VERSION`: the immutable semantic application release version;
- `ZONEPILOT_GIT_SHA`: the exact lowercase 40-character commit built into the deployment;
- `ZONEPILOT_SCHEMA_VERSION`: the semantic Gold schema version expected by that release;
- `ZONEPILOT_DATA_ROOT`: the mounted private artifact root used by the existing read-only catalog.

Set these values in the deployment platform from the built artifact and approved evidence workflow. Branch names, abbreviated hashes, floating tags, local/development labels, and unknown or placeholder values are rejected.

## Verification performed on every request

After Supabase access-token verification, the endpoint:

1. validates the configured application version, exact commit SHA, and schema version;
2. requires the Gold manifest to carry the same commit and schema, a passing DQ state, positive row count, stable dataset/version identifiers, canonical graph identity, and SHA-256 artifact identity;
3. recomputes the mounted Gold Parquet SHA-256 and compares it with the manifest;
4. requires passing OSRM build and smoke evidence from the same commit and the Gold road PBF input, including a positive route, reachable matrix cells, and no null cells;
5. recomputes the complete `pilot_roads.osrm*` bundle identity from sorted file names and bytes and compares it with both OSRM manifests.

The successful response contains only application, Gold, and graph identifiers and hashes. It never contains filesystem locations, environment values, credentials, signed URLs, or partial data.

## Failure behavior

Missing configuration, stale manifests, malformed identifiers, absent artifacts, hash mismatches, schema/commit mismatches, failed DQ, or invalid routing smoke evidence all produce the same retryable HTTP 503 `RELEASE_IDENTITY_UNAVAILABLE` envelope. The API does not disclose which private path or value failed and never returns a partially trusted identity.

Unauthenticated requests receive the standard HTTP 401 envelope before artifact verification. `/healthz` and `/readyz` remain orchestration probes and must not be used as release identity.

The authenticated Observatory `/system-health` page consumes this endpoint through the existing session proxy. It labels a failed identity request as unavailable rather than substituting package versions or browser build metadata.
