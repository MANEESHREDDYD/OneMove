# X1 BREAKER FINDINGS — OneMove Decision Engine API

Author: X1 (permanent breaker). Role: make the system fail. I do not fix and I do not close.

Target: `services.api.main:app` (FastAPI), backed by the live local Postgres from `.env.local`
(`127.0.0.1:54332/postgres`).

Environment used for every reproduction in this document:

```bash
cd "c:/Users/md200/OneDrive/Desktop/OneMove"
set -a && . ./.env.local && set +a
export TEST_DATABASE_URL="$DATABASE_URL"
export ZONEPILOT_DATA_ROOT="$(pwd)/data_root"
export PYTHONPATH="$(pwd)"
export PYTHONIOENCODING=utf-8
```

Auth is supplied by the documented dependency override
(`app.dependency_overrides[get_current_user]`), same pattern as
`tests/api/test_all_12_observatory_routes.py`.

Two real tenants were created with real rows before any cross-tenant attempt:

| | workspace_id | user (`sub`) |
|---|---|---|
| A | `00000000-0000-0000-0000-000000000001` | `00000000-0000-0000-0000-000000000002` |
| B | `0000000b-0000-0000-0000-00000000000b` | `0000000b-0000-0000-0000-0000000000b2` |

Each tenant received a real `optimization_jobs` row (status SUCCESS / OPTIMAL), a real
`optimization_results` row, a real `optimization_problem_snapshots` row, and a real
`decision_records` row whose `feature_snapshot_hash` points at that tenant's snapshot.

**Campaign size: 97 distinct hostile requests over two full runs (identical results both runs)
plus 3 targeted verification passes. Outcome distribution: 404 x47, 422 x17, 500 x14, 503 x2,
2xx x8, client-side-rejected x6, direct repository probes x3.**

Every finding below was reproduced at least twice. Anything I could not reproduce twice is not
reported.

Reproduction scripts live outside the repo (I am not permitted to add source files):

```
%LOCALAPPDATA%\Temp\claude\c--Users-md200-OneDrive-Desktop-OneMove\2bd23552-d45f-46cd-a869-e2b260d7e5be\scratchpad\
  x1_seed.py       # creates the two tenants' real rows (self-seeding, idempotent per run)
  x1_attack.py     # the 97-request campaign
  x1_verify.py     # focused double-reproduction of the isolation / poison-row / horizon findings
  x1_envelope.py   # error-envelope consistency sweep
```

Every finding also carries a self-contained inline reproduction that does not depend on those files.

---

## SUMMARY

| ID | Severity | One line |
|---|---|---|
| X1-001 | P1 | Nine domain-validation conditions on `POST /api/v1/optimizations` return 500 `INTERNAL_ERROR` with `retryable: true` |
| X1-002 | P1 | `POST /api/v1/optimizations` accepts arbitrary invented scenario names and persists them as evidence-class travel matrices |
| X1-003 | P1 | `POST /api/v1/forecast/predict` persists a forecast for any string as `zone_id`, including `../../etc/passwd` |
| X1-004 | P1 | `POST /api/v1/forecast/predict` with `horizon_hours: -5` persists a "forecast" whose `target_time` is in the past; `horizon_hours: 1e9` is a 500 |
| X1-005 | P2 | `%00` in a `decision_id` path segment is reported as a retryable 503 `DECISION_STORE_UNAVAILABLE` |
| X1-006 | P2 | One unreadable row in `decision_records` takes down `GET /api/v1/decisions` for the whole workspace, as a retryable 503 |
| X1-007 | P2 | Error messages leak psycopg driver text, pydantic model internals and the pydantic minor version to the client |
| X1-008 | P2 | Oversized / NUL-bearing `idempotency_key` reaches Postgres and returns 500 instead of 422 |

**Tenant isolation (surface A) held on every single attempt. No P0 was found in isolation.**
See "ATTACKS THAT CORRECTLY FAILED".

---

### X1-001 Nine domain-validation conditions on POST /api/v1/optimizations return 500 INTERNAL_ERROR with retryable:true
SEVERITY: P1

AREA: `services/api/routers/observatory.py` — `run_optimization` (line 374) and
`_build_real_94x12x3_problem` (line 255).

ROOT CAUSE (read, then proven): `run_optimization` wraps the problem build in
`try/except FileNotFoundError` only:

```python
    try:
        problem = _build_real_94x12x3_problem(payload)
    except FileNotFoundError as fnf_err:
        standard_error("MATRIX_UNAVAILABLE", str(fnf_err), 503)
```

`_build_real_94x12x3_problem` raises a bare `ValueError` for `SCENARIO_LADDER_MISMATCH`, and
constructs `OptimizationConstraints` / `OptimizationProblem`, both of which raise
`pydantic_core.ValidationError` for documented domain rules
(`services/zonepilot/optimization/contracts.py` lines 173–186, 280–283). None of those is a
`FileNotFoundError`, so all of them escape the route, escape FastAPI, and are caught by the
blanket handler in `services/api/core/middleware.py` line 97, which emits 500 `INTERNAL_ERROR`
with `retryable: true`.

REPRODUCTION (runnable as-is):

```bash
cd "c:/Users/md200/OneDrive/Desktop/OneMove"
set -a && . ./.env.local && set +a
export TEST_DATABASE_URL="$DATABASE_URL" ZONEPILOT_DATA_ROOT="$(pwd)/data_root" PYTHONPATH="$(pwd)"
python - <<'PY'
import uuid
from fastapi.testclient import TestClient
from services.api.core.auth import get_current_user
from services.api.main import app
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000002",
    "workspace_id": "00000000-0000-0000-0000-000000000001", "role": "operator"}
c = TestClient(app, raise_server_exceptions=False)
CASES = {
  "max_travel_seconds=1e12":      {"max_travel_seconds": 10**12},
  "max_travel_seconds=int64max":  {"max_travel_seconds": 9223372036854775807},
  "min(9) > max(2)":              {"min_open_facilities": 9, "max_open_facilities": 2},
  "min(199) > 12 facilities":     {"min_open_facilities": 199, "max_open_facilities": 200},
  "max(50) > 12 facilities":      {"min_open_facilities": 1, "max_open_facilities": 50},
  "min=max=1e9":                  {"min_open_facilities": 10**9, "max_open_facilities": 10**9},
  "scenarios=[]":                 {"scenarios": []},
  "scenarios=['zzz']":            {"scenarios": ["zzz"]},
  "scenarios=['a']*50":           {"scenarios": ["a"]*50},
  "scenarios=['s1','s1','s1']":   {"scenarios": ["s1","s1","s1"]},
}
for name, extra in CASES.items():
    body = {"idempotency_key": "x1-" + str(uuid.uuid4())}; body.update(extra)
    r = c.post("/api/v1/optimizations", json=body)
    print("%-30s -> %s %s" % (name, r.status_code, r.json().get("error", {}).get("code")))
PY
```

EXPECTED: a typed 4xx envelope naming the violated rule, e.g. 422 `INVALID_CONSTRAINTS` /
`SCENARIO_LADDER_MISMATCH`, `retryable: false`. These are permanent properties of the request;
retrying can never change the outcome.

ACTUAL: HTTP 500, `code: INTERNAL_ERROR`, `message: "An unexpected error occurred."`,
**`retryable: true`**, for all ten inputs.

EVIDENCE (identical in run 1 and run 2 of the 97-request campaign):

```
[500] B-opt-post-travel_enormous       code=INTERNAL_ERROR retryable=True
[500] B-opt-post-travel_int64_max      code=INTERNAL_ERROR retryable=True
[500] B-opt-post-min_gt_max            code=INTERNAL_ERROR retryable=True
[500] B-opt-post-min_gt_facilities     code=INTERNAL_ERROR retryable=True
[500] B-opt-post-max_gt_facilities     code=INTERNAL_ERROR retryable=True
[500] B-opt-post-min_enormous          code=INTERNAL_ERROR retryable=True
[500] B-opt-post-scenarios_empty       code=INTERNAL_ERROR retryable=True
[500] B-opt-post-scenarios_one_unknown code=INTERNAL_ERROR retryable=True
[500] B-opt-post-scenarios_many        code=INTERNAL_ERROR retryable=True
[500] B-opt-post-scenarios_dupe        code=INTERNAL_ERROR retryable=True

{"error":{"code":"INTERNAL_ERROR","message":"An unexpected error occurred.",
 "retryable":true,"details":{},"request_id":"2e6bfff2-3127-4fcc-bc6d-40813b3b078e",
 "trace_id":"2e6bfff2-3127-4fcc-bc6d-40813b3b078e"}}
```

The exact exceptions escaping, captured by calling `_build_real_94x12x3_problem` directly:

```
travel_enormous   -> pydantic_core.ValidationError | max_travel_seconds: Input should be less than or equal to 604800
min_gt_max        -> pydantic_core.ValidationError | Value error, min_open_facilities must not exceed max_open_facilities
max_gt_facilities -> pydantic_core.ValidationError | Value error, max_open_facilities must not exceed the number of facilities
min_enormous      -> pydantic_core.ValidationError | min_open_facilities: Input should be less than or equal to 200
scenarios_empty   -> builtins.ValueError | SCENARIO_LADDER_MISMATCH: assumption set r1-pilot-proxy@1.1.0+sha256.9d52... defines 3 scenario tiers (BASELINE, DEGRADED, SEVERE) but 0 scenarios were requested.
scenarios_dupe    -> pydantic_core.ValidationError | Value error, scenario_id values must be unique
```

WHY IT MATTERS: `retryable: true` is a contract instruction. A conforming client, a queue
consumer, or an SDK with automatic retry will hammer these requests forever, because the server
told it the failure was transient when it is permanent. Simultaneously, the operator loses the
diagnosis entirely — `min_open_facilities must not exceed max_open_facilities` is a precise,
actionable message and the API replaces it with "An unexpected error occurred." Every one of
these is also a false page: it lands in the 5xx error budget and in Sentry
(`middleware.py` calls `sentry_sdk.capture_exception`) as an unhandled server fault, so an
on-call engineer is woken up by a caller typing `max_open_facilities: 50`. The router's own
docstring for `_fail_if_dependency_unavailable` states the design intent — "a dependency outage
is a retryable 503, never a 4xx client error" — and this is the exact inverse violation: a client
error reported as a retryable server fault. Note also that the SUBMISSION path is the one that
fails: `POST /api/v1/optimizations` is the primary write of the whole R1 surface.

---

### X1-002 POST /api/v1/optimizations accepts arbitrary invented scenario names and persists them as evidence-class travel matrices
SEVERITY: P1

AREA: `services/api/routers/observatory.py` — `OptimizationRequest.scenarios` (line 251) and
`_build_real_94x12x3_problem` (lines 325–360).

ROOT CAUSE: `scenarios: list[str]` is unvalidated. The builder only checks the *count* against
the assumption set's tier count, then `zip`s the caller's strings positionally onto the sealed
tiers and stamps each with that tier's `evidence_class`, probability and duration multiplier:

```python
    for s_name, tier in zip(req.scenarios, tiers, strict=True):
        matrix_id = f"matrix-{s_name}"
        ...
        mat = TravelMatrix(matrix_id=matrix_id, ..., evidence_class=tier.evidence_class, ...)
```

Any three strings therefore validate. `["s3_congested_outage", "s2_congested", "s1_free_flow"]`
would silently label the SEVERE tier as free-flow.

REPRODUCTION:

```bash
python - <<'PY'
import uuid, psycopg
from fastapi.testclient import TestClient
from services.api.core.auth import get_current_user
from services.api.main import app
from services.common.db_dsn import get_database_dsn
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000002",
    "workspace_id": "00000000-0000-0000-0000-000000000001", "role": "operator"}
c = TestClient(app, raise_server_exceptions=False)
r = c.post("/api/v1/optimizations", json={
    "idempotency_key": "x1-verify-" + str(uuid.uuid4()),
    "scenarios": ["totally_made_up_a", "totally_made_up_b", "totally_made_up_c"]})
print("HTTP", r.status_code, r.text[:160])
jid = r.json()["job_id"]
with psycopg.connect(get_database_dsn()) as cx, cx.cursor() as cur:
    cur.execute("SELECT request_payload, matrix_id FROM public.optimization_jobs WHERE id=%s::uuid", (jid,))
    payload, matrix_id = cur.fetchone()
print("persisted scenarios:", payload.get("scenarios"))
print("persisted matrix_id:", matrix_id)
PY
```

EXPECTED: 422 with a typed code (e.g. `SCENARIO_UNKNOWN`) naming the accepted scenario ids, in
the same spirit as `POST /api/v1/scenarios`, which *does* enumerate its legal values
(`SCENARIO_TYPE_UNKNOWN ... supported: ['CAPACITY_REDUCTION', 'COMPOUND_FAILURE', ...]`).

ACTUAL: HTTP 202. The invented names are written into the durable job row and become the
`matrix_id` on the frozen problem, which is covered by `problem_fingerprint` and therefore
propagates into the problem snapshot, the result document and any decision frozen from it.

EVIDENCE (reproduced in run 1, run 2, and the targeted verification pass):

```
POST /optimizations with 3 invented scenario names -> 202
{"job_id":"e4b4ecf0-d0d2-4359-9a0c-400bdb0a1581","status":"QUEUED",...}
persisted request_payload.scenarios: ['totally_made_up_a', 'totally_made_up_b', 'totally_made_up_c']
persisted matrix_id: matrix-totally_made_up_a
```

Contrast, from the same campaign — the sibling endpoint defends itself correctly:

```
[422] B-scenario-unknown-type  code=SCENARIO_TYPE_UNKNOWN retryable=False
  "unsupported scenario_type \"'; DROP TABLE x;--\"; supported: ['CAPACITY_REDUCTION',
   'COMPOUND_FAILURE', 'CONGESTION_SPIKE', 'FACILITY_OUTAGE', 'HEAVY_RAIN', 'ROAD_CLOSURE']"
```

WHY IT MATTERS: the scenario name is the human-readable label on a probability-weighted
uncertainty tier. Positional `zip` means the label carries no binding relationship to the tier it
names, so a caller can attach the SEVERE tier's 1.4x multiplier and its `evidence_class` to a
matrix called `matrix-s1_free_flow` — and the mislabel is then sealed by `problem_fingerprint`
into the snapshot, the result, and the decision ledger. The codebase invests heavily in exactly
this property (the `_build_real_94x12x3_problem` docstring on F-019 argues at length that
unverifiable labels "made them look as though they had been [measured]"), and the scenario
identifier is the one label on the frozen artifact that nothing validates. An audit reading the
ledger back cannot tell whether `matrix-s1_free_flow` is free-flow.

---

### X1-003 POST /api/v1/forecast/predict persists a forecast for any string as zone_id, including ../../etc/passwd
SEVERITY: P1

AREA: `services/api/routers/observatory.py` — `ForecastRequest.zone_id` (line 931) and
`predict_forecast` (line 935).

ROOT CAUSE: `zone_id: str = "88618925d3fffff"` — a bare `str` with no validator, no H3 format
check, and no membership check against the 94 zones the rest of the system is built on. The value
is copied straight into `PredictionRecord.zone_id` and saved.

REPRODUCTION:

```bash
python - <<'PY'
import psycopg
from fastapi.testclient import TestClient
from services.api.core.auth import get_current_user
from services.api.main import app
from services.common.db_dsn import get_database_dsn
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000002",
    "workspace_id": "00000000-0000-0000-0000-000000000001", "role": "operator"}
c = TestClient(app, raise_server_exceptions=False)
for rep in (1, 2):
    r = c.post("/api/v1/forecast/predict", json={"zone_id": "../../etc/passwd", "horizon_hours": -5})
    print("rep", rep, "->", r.status_code, r.json().get("prediction_id"), repr(r.json().get("zone_id")))
    r2 = c.post("/api/v1/forecast/predict", json={"zone_id": "'; DROP TABLE forecast_records;--"})
    print("rep", rep, "sqli zone ->", r2.status_code, repr(r2.json().get("zone_id")))
with psycopg.connect(get_database_dsn()) as cx, cx.cursor() as cur:
    cur.execute("SELECT forecast_id, zone_id, horizon_hours FROM public.forecast_records "
                "WHERE zone_id LIKE %s OR zone_id LIKE %s", ('%etc/passwd%', '%DROP %'))
    for row in cur.fetchall(): print("PERSISTED:", row)
    cur.execute("SELECT to_regclass('public.forecast_records')")
    print("table still exists:", cur.fetchone()[0])
PY
```

EXPECTED: 422 `INVALID_ARGUMENT` / `UNKNOWN_ZONE`. The endpoint already returns exactly that shape
for an unknown `model` value, so the pattern exists and is simply not applied to `zone_id`.

ACTUAL: HTTP 201 Created, with the hostile string echoed back and durably written to
`public.forecast_records`.

EVIDENCE:

```
rep 1 -> 201 pred-ffc221c72b14 '../../etc/passwd'
rep 1 sqli zone -> 201 "'; DROP TABLE forecast_records;--"
rep 2 -> 201 pred-f3f398bdbdad '../../etc/passwd'
rep 2 sqli zone -> 201 "'; DROP TABLE forecast_records;--"

PERSISTED: ('pred-80b9312ca4de', '../../etc/passwd', -5)
PERSISTED: ('pred-b7d1bd7fc43e', '../../etc/passwd', -5)
PERSISTED: ('pred-ffc221c72b14', '../../etc/passwd', -5)
PERSISTED: ('pred-8f266618971f', "'; DROP TABLE forecast_records;--", 1)
table still exists: forecast_records
```

Full 201 body, first reproduction:

```json
{"prediction_id":"pred-80b9312ca4de","workspace_id":"00000000-0000-0000-0000-000000000001",
 "zone_id":"../../etc/passwd","prediction_time":"2026-08-24T21:40:00.446048+00:00",
 "target_time":"2026-08-24T16:40:00.446048+00:00","horizon_hours":-5,
 "target":"WEATHER_TRAVEL_INFLATION_PERCENT","predicted_value":null,
 "baseline_model":"LAST_OBSERVATION","code_sha":"daf7ca5c222f80a84ec1ebd1f5b5c337e41a7fc1",
 "status":"EVIDENCE_ACCUMULATING"}
```

Note explicitly: the SQL injection **did not execute** — the query is correctly parameterized and
`forecast_records` survives. The defect is unvalidated acceptance and durable storage, not
injection.

WHY IT MATTERS: `forecast_records` is a measurement table. Any caller can inject unbounded rows
keyed to zones that do not exist, permanently, with no rate or vocabulary limit. Every downstream
consumer that joins forecasts to zones, computes per-zone accuracy, or counts "zones with
forecasts" is now reading a table it cannot trust, and there is no way to distinguish a garbage
row from a real one after the fact because nothing recorded that the zone was never validated.
This is the same class of defect the codebase explicitly fixed for the decision ledger (F-005:
"A ledger that can be populated with invented measurements is not an audit trail") — the forecast
store never received the same treatment.

---

### X1-004 POST /api/v1/forecast/predict accepts a negative horizon and 500s on a large one
SEVERITY: P1

AREA: `services/api/routers/observatory.py` — `ForecastRequest.horizon_hours` (line 933) and
`predict_forecast` line 943:

```python
    target_time = datetime.fromtimestamp(now.timestamp() + payload.horizon_hours * 3600, tz=timezone.utc)
```

`horizon_hours: int` is unbounded in both directions. Negative values silently produce a
`target_time` before `prediction_time`; huge values overflow the platform `time_t` and raise
`OSError: [Errno 22] Invalid argument`, which no handler catches.

REPRODUCTION:

```bash
python - <<'PY'
from fastapi.testclient import TestClient
from services.api.core.auth import get_current_user
from services.api.main import app
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000002",
    "workspace_id": "00000000-0000-0000-0000-000000000001", "role": "operator"}
c = TestClient(app, raise_server_exceptions=False)
for rep in (1, 2):
    r = c.post("/api/v1/forecast/predict", json={"horizon_hours": -5})
    d = r.json()
    print("rep", rep, "horizon=-5 ->", r.status_code,
          "issued", d.get("prediction_time"), "target", d.get("target_time"))
    b = c.post("/api/v1/forecast/predict", json={"horizon_hours": 10**9})
    print("rep", rep, "horizon=1e9 ->", b.status_code, b.text[:130])
PY
```

EXPECTED: `horizon_hours` bounded by the contract (`ge=1`, and an upper bound consistent with the
forecast targets). Both cases 422 `VALIDATION_FAILED`, `retryable: false`.

ACTUAL:
- `horizon_hours: -5` → **201 Created**, `target_time` 5 hours **before** `prediction_time`, row
  persisted.
- `horizon_hours: 0` → **201 Created**, `target_time == prediction_time`.
- `horizon_hours: 1_000_000_000` → **500 `INTERNAL_ERROR`, `retryable: true`.**

EVIDENCE (both reproductions):

```
rep 1 horizon=-5 -> 201 issued 2026-08-24T21:43:02.235034+00:00 target 2026-08-24T16:43:02.235034+00:00
rep 1 horizon=1e9 -> 500 {"error":{"code":"INTERNAL_ERROR","message":"An unexpected error occurred.","retryable":true,...
rep 2 horizon=-5 -> 201 issued 2026-08-24T21:43:02.284532+00:00 target 2026-08-24T16:43:02.284532+00:00
rep 2 horizon=1e9 -> 500 {"error":{"code":"INTERNAL_ERROR","message":"An unexpected error occurred.","retryable":true,...
```

Server log line for the 500, confirming the unhandled exception type:

```json
{"level":"ERROR","message":"unhandled_request_exception","route":"/api/v1/forecast/predict",
 "error_code":"INTERNAL_ERROR","exception_type":"OSError"}
```

Direct confirmation of the root cause:

```
forecast_huge -> builtins.OSError | [Errno 22] Invalid argument
```

And the row that a negative horizon leaves behind, read back from Postgres:

```
('pred-80b9312ca4de', '../../etc/passwd', -5,
 forecast_issue_time=2026-08-24 21:40:00.446048+00,
 target_time=2026-08-24 16:40:00.446048+00)   <-- target BEFORE issue
```

WHY IT MATTERS: a "forecast" whose target time precedes its issue time is not a forecast; it is a
backdated claim about the past, stored in the same table and indistinguishable from a real
prediction to every reader. The point-in-time discipline the decision ledger enforces with a
database CHECK (`chk_decision_pit_causality: decision_time <= recorded_at + 1s`) has no equivalent
on `forecast_records`, so nothing at any layer stops it. Any accuracy or skill metric computed
over this table is corruptible by an ordinary API caller. Separately, the 1e9 case is a
one-line unauthenticated-shaped 500 generator against a write endpoint.

---

### X1-005 %00 in a decision_id path segment is reported as a retryable 503 DECISION_STORE_UNAVAILABLE
SEVERITY: P2

AREA: `services/api/routers/observatory.py` — `get_decision` (line 834), and the identical
`except Exception -> 503` pattern in `list_decisions` (825) and `get_shadow` (911).

ROOT CAUSE: the route catches every non-HTTPException and relabels it as a store outage:

```python
    except HTTPException:
        raise
    except Exception as exc:
        standard_error("DECISION_STORE_UNAVAILABLE", str(exc), 503)
```

`decision_records.decision_id` is `text`, so a NUL byte in the id reaches psycopg, which raises
`psycopg.DataError` — a *client data* error, not a connection error. `_fail_if_dependency_unavailable`
is not called on this path, and even if it were, `DataError` is not an
`OperationalError`/`InterfaceError`.

REPRODUCTION:

```bash
python - <<'PY'
from fastapi.testclient import TestClient
from services.api.core.auth import get_current_user
from services.api.main import app
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000002",
    "workspace_id": "00000000-0000-0000-0000-000000000001", "role": "operator"}
c = TestClient(app, raise_server_exceptions=False)
for rep in (1, 2):
    r = c.get("/api/v1/decisions/abc%00def")
    print("rep", rep, "->", r.status_code, r.text)
PY
```

(Note: a *raw* NUL or newline in the URL is rejected client-side by httpx before it reaches the
server — see "ATTACKS THAT CORRECTLY FAILED". The percent-encoded form reaches the route.)

EXPECTED: 422 `INVALID_ARGUMENT` or 404 `NOT_FOUND`, `retryable: false`. The id is permanently
unusable; no amount of retrying changes that.

ACTUAL: HTTP 503 `DECISION_STORE_UNAVAILABLE`, **`retryable: true`**, with the raw psycopg driver
message.

EVIDENCE (both reproductions identical):

```
GET /api/v1/decisions/abc%00def -> 503
{"error":{"code":"DECISION_STORE_UNAVAILABLE",
 "message":"PostgreSQL text fields cannot contain NUL (0x00) bytes",
 "retryable":true,"details":{},
 "request_id":"2dd6dbcf-8076-412f-af68-30067e278d3a",
 "trace_id":"2dd6dbcf-8076-412f-af68-30067e278d3a"}}
  repeat -> 503 (same: True)
```

For contrast, the *same* input against the optimization route is handled correctly, because
`OptimizationRepository._get_job_row` guards with `_is_valid_uuid` before touching the driver:

```
[404] B-opt-pct_nul   code=NOT_FOUND retryable=False
```

WHY IT MATTERS: `DECISION_STORE_UNAVAILABLE` + `retryable: true` tells operators and dashboards
that Postgres is down. A caller sending malformed ids can therefore manufacture a false database
outage signal at will — every such request is a 503 in the SLO burn rate and, if the alerting is
wired to 503 rate on the decision store, a page. It also breaks the exact contract
`_fail_if_dependency_unavailable` was written to protect: "a dependency outage is a retryable 503,
never a 4xx client error" — here the inverse holds, a 4xx client error is served as a retryable
dependency outage.

---

### X1-006 One unreadable row in decision_records takes down GET /api/v1/decisions for the whole workspace, as a retryable 503
SEVERITY: P2

AREA: `services/api/routers/observatory.py` `list_decisions` (line 824) +
`services/zonepilot/decisions/repository.py` `list_decisions` (line 171), which constructs a
`DecisionRecord` per row with no per-row isolation.

`DecisionRecord.code_sha` is constrained to `^[0-9a-f]{40}$` by the pydantic contract.
`public.decision_records` has **no** corresponding CHECK constraint, verified directly:

```
### STEP 4: is there a DB CHECK on decision_records.code_sha?
  code_sha constraints: NONE -- DB accepts what the API reader rejects
```

So the store accepts a value that the reader will refuse, and the refusal is not scoped to the
offending row.

REPRODUCTION:

```bash
python - <<'PY'
import hashlib, psycopg
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from services.api.core.auth import get_current_user
from services.api.main import app
from services.common.db_dsn import get_database_dsn
WS = "00000000-0000-0000-0000-000000000001"
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000002", "workspace_id": WS, "role": "operator"}
c = TestClient(app, raise_server_exceptions=False)
def sql(q, a=()):
    with psycopg.connect(get_database_dsn()) as cx, cx.cursor() as cur:
        cur.execute(q, a); cx.commit()
print("before ->", c.get("/api/v1/decisions").status_code)
now = datetime.now(timezone.utc)
sql("""INSERT INTO public.decision_records
       (decision_id, workspace_id, decision_time, network_version, dataset_version,
        feature_snapshot_hash, selected_action, opened_facilities, objective_value,
        expected_travel_seconds, p95_travel_seconds, coverage_basis_points,
        graph_version, osrm_bundle_hash, solver_version, code_sha, evidence_ids,
        recorded_at, decision_class, optimization_policy_version)
       VALUES ('dec-x1-poison', %s, %s,'nv','dv',%s,'OPEN_FACILITIES',ARRAY['F1'],1,1,1,1,
               'gv',%s,'sv','cs-1',ARRAY['e'],%s,'OPTIMIZER_DECISION','1.0.0')
       ON CONFLICT (decision_id) DO NOTHING""",
    (WS, now, hashlib.sha256(b"x").hexdigest(), hashlib.sha256(b"y").hexdigest(), now))
for rep in (1, 2):
    r = c.get("/api/v1/decisions"); print("with poison row rep", rep, "->", r.status_code, r.text[:300])
sql("DELETE FROM public.decision_records WHERE decision_id = 'dec-x1-poison'")
print("after removal ->", c.get("/api/v1/decisions").status_code)
PY
```

EXPECTED: either the DB rejects the write (a CHECK mirroring the contract), or the reader isolates
the bad row — skip it and report it, or fail with a non-retryable integrity code naming the row.
The healthy decisions in the workspace must remain readable.

ACTUAL: `GET /api/v1/decisions` returns 503 `DECISION_STORE_UNAVAILABLE`, `retryable: true`, for
the *entire workspace*, for as long as the row exists. Every other decision in the workspace
becomes unreachable through the list endpoint.

EVIDENCE:

```
### STEP 1 (no poison row)
GET /api/v1/decisions -> 200

### STEP 3: reintroduce ONE unreadable row (code_sha='cs-1'), then list again
GET /api/v1/decisions with 1 poison row -> 503
{"error":{"code":"DECISION_STORE_UNAVAILABLE",
 "message":"1 validation error for DecisionRecord\ncode_sha\n  String should match pattern
  '^[0-9a-f]{40}$' [type=string_pattern_mismatch, input_value='cs-1', input_type=str]\n
  For further information visit https://errors.pydantic.dev/2.13/v/string_pattern_mismatch",
 "retryable":true,...}
  repeat -> 503 (same: True)
after removing poison row -> 200
```

I hit this unintentionally first: my seed row used `code_sha='cs-1'`, and the entire workspace-A
decision listing went 503 for the whole of campaign run 1 and run 2 as a side effect — which is
the blast radius, demonstrated accidentally before it was demonstrated deliberately.

WHY IT MATTERS: `decision_records` is described in-tree as an immutable audit ledger. A single row
written by any path that does not go through the pydantic contract — a migration, a backfill, the
Pub/Sub worker, a future writer, a restored backup — renders the entire tenant's ledger
unlistable, and reports the cause as a transient store outage that will never clear on retry. The
schema and the contract disagree on what a valid row is, and the disagreement is resolved at read
time, tenant-wide, in the worst possible direction. `GET /api/v1/decisions/{id}` for a *healthy*
decision still works, so this is specifically a listing/enumeration denial of service triggered by
one bad neighbour.

---

### X1-007 Error messages leak psycopg driver text, pydantic model internals and the pydantic minor version
SEVERITY: P2

AREA: `services/api/routers/observatory.py`, every site of the form
`standard_error("<CODE>", str(exc), <status>)` — `list_decisions` (831), `get_decision` (852),
`replay_decision` (881), `create_shadow_evaluation` (908), `get_shadow` (932), `freeze_decision`
(717), `record_decision` (818), `predict_forecast` (979).

REPRODUCTION: any of X1-005 or X1-006 above; also:

```bash
python - <<'PY'
from fastapi.testclient import TestClient
from services.api.core.auth import get_current_user
from services.api.main import app
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000002",
    "workspace_id": "00000000-0000-0000-0000-000000000001", "role": "operator"}
c = TestClient(app, raise_server_exceptions=False)
for probe in ("/api/v1/decisions/abc%00def", "/api/v1/decisions"):
    t = c.get(probe).text.lower()
    print(probe, {sig: sig in t for sig in ("psycopg", "pydantic", "errors.pydantic.dev", "traceback")})
PY
```

EXPECTED: a stable, human-readable message. Driver text, internal model field names, library
versions and doc URLs belong in the log, not the response body — exactly the policy already
applied to the database handler in `services/api/main.py`, whose comment reads "The driver message
can embed host/user details, so it is logged, never returned."

ACTUAL: `str(exc)` is returned verbatim to the client.

EVIDENCE:

```
"message":"PostgreSQL text fields cannot contain NUL (0x00) bytes"          <- psycopg driver text

"message":"1 validation error for DecisionRecord\ncode_sha\n  String should match pattern
 '^[0-9a-f]{40}$' [type=string_pattern_mismatch, input_value='cs-1', input_type=str]\n
 For further information visit https://errors.pydantic.dev/2.13/v/string_pattern_mismatch"
                        ^ internal model name  ^ internal field  ^ regex  ^ pydantic 2.13
```

Also observed on `REPLAY_ERROR` (422) with the identical pydantic body.

WHY IT MATTERS: this is free reconnaissance — exact dependency version (pydantic 2.13), internal
model class names, internal column/field names, and validation regexes, handed to any
authenticated caller by triggering ordinary errors. It is a lesser cousin of the stack trace the
app is otherwise careful to suppress: the 500 handler correctly returns "An unexpected error
occurred.", and the DB handler correctly logs-not-returns, but these eight router sites bypass
both policies. No stack trace was ever returned in 97 attacks — this is the remaining leak.

---

### X1-008 Oversized / NUL-bearing idempotency_key reaches Postgres and returns 500 instead of 422
SEVERITY: P2

AREA: `services/api/routers/observatory.py` `OptimizationRequest.idempotency_key`
(`str | None = None`, no length or charset bound) → `OptimizationRepository.create_job`.

The database *does* have the bound the API lacks:
`chk_optimization_job_idempotency_key CHECK (char_length(idempotency_key) BETWEEN 1 AND 200)`.
The violation therefore surfaces as a `psycopg.errors.CheckViolation` at INSERT time, uncaught.

REPRODUCTION:

```bash
python - <<'PY'
from fastapi.testclient import TestClient
from services.api.core.auth import get_current_user
from services.api.main import app
app.dependency_overrides[get_current_user] = lambda: {
    "sub": "00000000-0000-0000-0000-000000000002",
    "workspace_id": "00000000-0000-0000-0000-000000000001", "role": "operator"}
c = TestClient(app, raise_server_exceptions=False)
for name, key in (("10KB key", "K"*10240), ("201 chars", "Q"*201), ("NUL byte", "a\x00b")):
    r = c.post("/api/v1/optimizations", json={"idempotency_key": key})
    print("%-10s -> %s %s" % (name, r.status_code, r.json().get("error", {}).get("code")))
PY
```

EXPECTED: 422 `VALIDATION_FAILED` from a `Field(min_length=1, max_length=200)` on the request
model, mirroring the CHECK that already exists in the schema. `retryable: false`.

ACTUAL: HTTP 500 `INTERNAL_ERROR`, `retryable: true`, for all three.

EVIDENCE (run 1 and run 2 identical):

```
[500] B-opt-post-idem_10kb      code=INTERNAL_ERROR retryable=True
[500] B-opt-post-idem_nullbyte  code=INTERNAL_ERROR retryable=True
[500] B-opt-post-idem_201chars  code=INTERNAL_ERROR retryable=True
```

Root causes, captured by driving the service layer directly:

```
idem_10kb    -> psycopg.errors.CheckViolation | new row for relation "optimization_jobs"
                violates check constraint "chk_optimization_job_idempotency_key"
idem_nullbyte-> psycopg.DataError | PostgreSQL text fields cannot contain NUL (0x00) bytes
```

Boundary confirmed: 200 chars is accepted (202), 201 chars is a 500. The failure is exactly at the
DB's declared bound, which the API never mirrors.

WHY IT MATTERS: same retry-storm and false-page consequences as X1-001, on the same write
endpoint, and it additionally shows the general pattern: the schema carries the real invariant, the
API request model does not, and the gap between them is served to callers as a 5xx. Note the
happier half of the same test — an idempotency key of `'; DROP TABLE optimization_jobs;--` was
accepted, stored verbatim, and executed nothing (the table survives). Injection is genuinely
defended; bounds are not.

---

## ATTACKS THAT CORRECTLY FAILED

This is the other half of the evidence. 97 hostile requests were sent; the following defended
correctly and are worth stating quantitatively, because they are the parts that can now be relied
on.

### Tenant isolation — 5/5 required attacks blocked, twice each, plus 7 extra probes

With workspace A's credentials against workspace B's **real, verified-present** rows. Sanity
checks in the same run confirm workspace B can read the very same rows (200), so the 404s are
genuine isolation and not a missing fixture:

| Attack | Result rep 1 | Result rep 2 | B reads own row |
|---|---|---|---|
| `GET /api/v1/decisions/{B_decision}` | 404 NOT_FOUND | 404 NOT_FOUND | 200 |
| `GET /api/v1/optimizations/{B_job}` | 404 NOT_FOUND | 404 NOT_FOUND | 200 |
| `POST /api/v1/decisions/{B_decision}/replay` | 404 NOT_FOUND | 404 NOT_FOUND | — |
| `POST /api/v1/decisions/freeze` with `{"optimization_job_id": B_job}` | 404 NOT_FOUND | 404 NOT_FOUND | — |
| `POST /api/v1/decisions/{B_decision}/shadow` | 404 NOT_FOUND | 404 NOT_FOUND | — |

Additional isolation probes, all defended:

- `POST /api/v1/decisions` citing workspace B's `optimization_job_id` → **404 NOT_FOUND**. The
  hand-authored path cannot be used to launder a foreign job into the local ledger.
- `GET /api/v1/decisions` as A → **200, contains no workspace-B decision id and no workspace-B
  workspace_id** (checked by substring against the actual seeded values).
- `GET /api/v1/optimizations` as A → **200, does not contain workspace B's job id**.
- `x-workspace-id: <B>` request header while authenticated as A → **404**. The header is in the
  CORS allow-list but is not trusted for authorization; the workspace comes only from the token
  claims via `_resolve_user_context`.
- `OptimizationRepository.get_problem_snapshot(B_snapshot_id, workspace_id=A)` → **None**.
- `OptimizationRepository.get_problem_snapshot(B_snapshot_sha256, workspace_id=A)` → **None**
  (the hash lookup is scoped identically to the id lookup — the snapshot is reachable by either
  key and both are guarded).
- `OptimizationRepository.get_problem_snapshot(B_snapshot_id, workspace_id=B)` → **found**
  (control, proving the row exists and the None results above are real refusals).

The isolation design is genuinely good and worth naming: workspace scope is a *mandatory*
parameter in the repositories, not an optional filter — `get_job`, `get_decision`,
`get_problem_snapshot` and `replay_decision` all raise `ValueError` on an empty workspace rather
than silently widening; the privileged unscoped read is a separately-named method
(`get_job_system`) so an unscoped read cannot happen by accident; and `_get_job_row` uses two
literal SQL statements instead of a conditionally-appended predicate so the two cases are
distinguishable by inspection. `replay_decision` explicitly refuses to back-fill the workspace
from the victim's record. I attacked this from five angles and found nothing.

### SQL injection — 0 successes in 14 injection attempts

`'; DROP TABLE decision_records;--`, `'; DROP TABLE optimization_jobs;--`,
`'; DROP TABLE shadow_evaluations;--`, `'; DROP TABLE resilience_scenarios;--`,
`'; DROP TABLE forecast_records;--` and `' OR '1'='1` were sent as decision ids, job ids,
scenario ids, shadow ids, experiment ids, snapshot ids, zone ids and idempotency keys. All were
treated as literal data (404 / 422 / stored verbatim). Every named table was confirmed still
present afterwards. Everything goes through psycopg parameter binding; I found no string-formatted
SQL anywhere on these paths.

### Path traversal — defended on every surface tried

- `GET /api/v1/evidence/osm/..%2F..%2F..%2Fetc%2Fpasswd` → **422 INVALID_ARGUMENT**, "Invalid tile
  path traversal attempt". The `:path` converter is the one place traversal could bite and it has
  an explicit `".." in tile_path or "//" in tile_path` guard.
- `GET /api/v1/zones/..%2F..%2Fetc%2Fpasswd/state` → 404 NOT_FOUND.
- `../../etc/passwd` as decision id / job id / experiment id → 404 NOT_FOUND.
- `%2e%2e%2f%2e%2e%2fetc%2fpasswd` (double-encoded) as decision id / job id → 404 NOT_FOUND.
- No file content was ever returned and no 200 was ever produced by a traversal payload.

### Oversized and exotic identifiers

- A **10,240-character** decision id, job id and replay id → 404 NOT_FOUND, no 5xx, no timeout.
- Unicode + emoji + RTL override (`дец-💥-‮`) as an id → 404 NOT_FOUND.
- `%0A`, `%0D`, bare `%`, malformed `%zz` in a path segment → 404 NOT_FOUND.
- Raw NUL and raw newline in the URL were rejected **client-side** by httpx
  (`httpx.InvalidURL: Invalid non-printable ASCII character in URL`) and never reached the server —
  correctly reported here as *not* a server finding. The percent-encoded forms did reach the
  server; `%00` produced X1-005 on the decision route only, and was handled correctly (404) on the
  optimization route.

### Numeric bounds that ARE enforced

`min_open_facilities` 0 and -5, `max_open_facilities` 0 and -1, `max_travel_seconds` 0 and -1000 →
all **422 VALIDATION_FAILED, retryable false**, from `Field(ge=...)` on `OptimizationRequest`. Six
for six. The `Field` guards that exist work exactly as intended; X1-001 is the set of rules that
live one layer deeper and were never mirrored up.

Also correctly rejected: `scenarios: [1,2,3]` (non-string) → 422 VALIDATION_FAILED;
`capacity_mode: "TOTALLY_BOGUS"` → 422 VALIDATION_FAILED;
`POST /api/v1/decisions/freeze` with no body → 422 VALIDATION_FAILED;
`feature_cutoff: "not-a-date"` → 422 VALIDATION_FAILED;
`POST /api/v1/scenarios` with a hostile `scenario_type` → 422 `SCENARIO_TYPE_UNKNOWN`, and the
message helpfully enumerates the six legal values;
`POST /api/v1/forecast/predict` with `model: "NOT_A_MODEL"` → 422 `INVALID_ARGUMENT`;
a shadow window in the past → 422 `INVALID_SHADOW_WINDOW`.

### Error envelope consistency — 11/11 clean, no bare strings, no stack traces

Sweep across auth, routing and payload failures (no auth override installed):

| Case | Status | Envelope |
|---|---|---|
| no `Authorization` header, `GET /api/v1/decisions` | 401 | `UNAUTHORIZED`, retryable false |
| no `Authorization` header, `GET /api/v1/optimizations` | 401 | `UNAUTHORIZED`, retryable false |
| `Authorization: Bearer notatoken` | 401 | `UNAUTHORIZED`, retryable false |
| `alg=none` forged JWT | 401 | `UNAUTHORIZED`, retryable false |
| `Authorization: Basic ...` | 401 | `UNAUTHORIZED`, retryable false |
| unknown route `/api/v1/does-not-exist` | 404 | `NOT_FOUND`, retryable false |
| unknown root route `/nope` | 404 | `NOT_FOUND`, retryable false |
| `DELETE /api/v1/decisions` | 405 | `METHOD_NOT_ALLOWED`, retryable false |
| `PUT /api/v1/optimizations` | 405 | `METHOD_NOT_ALLOWED`, retryable false |
| malformed JSON body | 422 | `VALIDATION_FAILED`, retryable false |
| 12 MB body | 413 | `PAYLOAD_TOO_LARGE`, retryable false |

Every one of the 97 campaign responses with status >= 400 carried a complete
`{"error": {"code", "message", "retryable", "details", "request_id", "trace_id"}}` envelope.
**Zero bare-string error bodies. Zero stack traces returned to a client, including on all 14
observed 500s** — the middleware's blanket handler correctly substitutes "An unexpected error
occurred." and logs the exception with `exception_type` instead. The `x-request-id` /
`x-trace-id` correlation headers were present on every response. This part of the contract is
solid; X1-001/X1-004/X1-008 are about the *status and retryability* being wrong, not about the
envelope shape.

The `alg=none` rejection deserves a specific mention: `verify_token` checks the unverified header
algorithm against an explicit allow-list intersected with `{ES256, RS256, HS256}` before selecting
a key, so the classic algorithm-confusion attack has no path.

---

## STATE LEFT BEHIND

Reproductions are self-seeding, but the campaign did leave rows in the local database. Recorded
here so nobody mistakes them for real data:

- `public.decision_records` — rows with `decision_id LIKE 'dec-x1-%'` in both workspace A and the
  synthetic workspace B (`0000000b-0000-0000-0000-00000000000b`).
- `public.optimization_problem_snapshots` — rows with `snapshot_id LIKE 'x1-snap-%'`.
- `public.forecast_records` — rows with `zone_id = '../../etc/passwd'` and
  `zone_id = '''; DROP TABLE forecast_records;--'` (the X1-003 evidence; deliberately left in
  place so the finding can be verified without re-running the attack).
- `public.optimization_jobs` — the `x1-%` idempotency-key jobs and their outbox events were
  deleted after the campaign so no synthetic job is dispatched to a worker. One job whose
  idempotency key is the literal SQL-injection string remains as evidence for the
  injection-defended result.

I did not modify any source file. The only file I wrote in the repository is this document.
