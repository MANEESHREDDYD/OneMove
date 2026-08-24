# H3 Independent Verification

**Verifier:** H3 (independent; did not implement any of this code)
**Repo:** `c:/Users/md200/OneDrive/Desktop/OneMove`
**Branch:** `hotfix/onemove-p0-security-incident`
**Pinned HEAD for all reported results:** `b035749`
**Date:** 2026-08-25

## Environment

```
cd "c:/Users/md200/OneDrive/Desktop/OneMove"
set -a && . ./.env.local && set +a
export TEST_DATABASE_URL="$DATABASE_URL"
export ZONEPILOT_DATA_ROOT="$(pwd)/data_root"
```

Python 3.11.0, pytest 8.3.4 (note: `pyproject.toml` pins `pytest==9.0.3` in dev deps;
the installed interpreter has 8.3.4 — a dependency drift, not a claim failure).
`osmium`, `h3` 4.5.0, `pandas` 2.2.2 all importable, so no `importorskip` went vacuous.
No `addopts` in `[tool.pytest.ini_options]` deselects the `slow` marker, so the
`@pytest.mark.slow` certification tests really do run under a bare `-q`.

### Verification-hygiene warning (read this first)

**The branch moved underneath this verification while it was running.** At session
start HEAD was `ceee6e5`; it advanced to `b035749` mid-run, and the diff
`ceee6e5..b035749` touches 64 files including every file under test:
`services/zonepilot/optimization/_cp_sat.py`, `.../contracts.py`,
`services/api/routers/observatory.py`, `services/zonepilot/decisions/ledger.py`,
`tests/geo/test_pilot_roads_lineage.py`, `tests/optimization/test_pilot_exact_oracle.py`,
`tests/optimization/test_zone_accounting.py`, and both files in `tests/decisions/`.

I caught this because `tests/geo/test_pilot_roads_lineage.py` grew a
`_require_pilot_roads()` helper (commit `9d75c2c`) between the moment I read it and
the moment I ran it. **Every number in this document was therefore re-run and
re-confirmed with `HEAD == b035749` before and after each command.** Results below
are pinned. Any claim re-asserted against a later HEAD needs re-verification.

---

## CLAIM 1: 94-zone accounting — assigned + uncovered == 94

**VERDICT: VERIFIED**

**COMMAND**

```
python -m pytest tests/optimization/test_zone_accounting.py -q -p no:cacheprovider
```

plus an independent real solve (scratch script, not committed) that builds the
problem through `_build_real_94x12x3_problem` and pushes the solved result through
the actual API read-path helper `services.api.routers.observatory._coverage_summary`.

**OUTPUT**

```
.............                                                            [100%]
13 passed in 3.43s
```

Independent real solve:

```
facilities=12 demand_points=94 scenarios=3
min_open=1 max_open=4 cap_s=1800
assumption_version=r1-pilot-proxy@1.1.0+sha256.9d5222905102c8e1351e16073eb72732e5de20f0c74d783df3c444d22b74576e

SOLVER STATUS: OPTIMAL
opened_facility_ids: ['fac:8861892599fffff', 'fac:88618925a7fffff',
                      'fac:88618925c5fffff', 'fac:8861892eddfffff']
n assignments (all scenarios): 282

--- _coverage_summary on the REAL solve ---
  coverage_basis_points: 10000
  demand_zones_total: 94
  assigned_zones: 94
  uncovered_zones: 0
  uncovered_zone_ids: len=0
  covered_demand_units: 36922
  uncovered_demand_units: 0

  ACCOUNTING: assigned(94) + uncovered(0) = 94  vs total(94)  -> OK
```

**NOTES**

- The accounting identity holds at the API level on a real solve. 282 assignments
  = 94 zones x 3 scenarios, which is the correct shape.
- **The shipped test is weaker than the claim it is cited for.**
  `test_every_zone_is_assigned_or_uncovered` does not solve anything. It hand-builds
  a `snapshot` dict of 94 fake zone ids and a `res_doc` with 2 fake assignments, then
  asserts `2 + 92 == 94`. That tests the arithmetic inside `_coverage_summary`, not
  that the optimizer to snapshot to read-path pipeline actually produces 94
  accountable zones. I closed that gap myself with the real solve above, and it
  passes — so the claim is true, but *this test file alone does not establish it*.
- `_coverage_summary` derives `uncovered_zones` purely from the frozen problem
  snapshot. If the snapshot is missing, `get_optimization` swallows the exception
  (`except Exception: snapshot = None`) and the response reports
  `demand_zones_total: None` / `uncovered_zones: None`. That degrades honestly
  (verified by `test_no_snapshot_degrades_without_inventing_counts`), but it means
  the 94-zone guarantee is only as durable as snapshot retention.

---

## CLAIM 2: the pilot optimum is independently certified; CP-SAT agrees with an exhaustive oracle

**VERDICT: VERIFIED (with a stated independence caveat)**

**COMMAND**

```
python -m pytest tests/optimization/test_pilot_exact_oracle.py -q -p no:cacheprovider
python -m pytest tests/optimization/test_pilot_exact_oracle.py -v -p no:cacheprovider --durations=10
```

plus my own re-implementation of the enumeration to recover the actual numbers.

**OUTPUT**

```
.....                                                                    [100%]
5 passed in 4.49s

test_oracle_finds_a_feasible_full_service_configuration PASSED
test_oracle_search_space_is_small_enough_to_be_exhaustive PASSED
test_cp_sat_optimum_matches_the_independent_oracle        PASSED
test_decision_is_reproducible_under_parallel_search       PASSED
test_canonical_assignment_breaks_ties_on_facility_id      PASSED

slowest durations:
  2.20s test_decision_is_reproducible_under_parallel_search
  1.08s test_oracle_finds_a_feasible_full_service_configuration
  0.48s test_cp_sat_optimum_matches_the_independent_oracle
```

Independent enumeration:

```
subset sizes 1..4 over 12 facilities -> 793 subsets enumerated
feasible (full-service) subsets: 202   infeasible: 591

ORACLE OPTIMUM VALUE = 23,548,137,358,244
number of optimal sets = 1  -> UNIQUE: True
  optimal set: ['fac:8861892599fffff', 'fac:88618925a7fffff',
                'fac:88618925c5fffff', 'fac:8861892eddfffff']

top 5 by objective:
  23,548,137,358,244  (+0.0000%)  8861892599 / 88618925a7 / 88618925c5 / 8861892edd
  23,667,805,307,587  (+0.5082%)  8861892537 / 8861892599 / 88618925a7 / 88618925c5
  23,679,526,573,776  (+0.5580%)  8861892599 / 88618925a7 / 88618925c5 / 8861892ecb
  23,849,456,078,146  (+1.2796%)  8861892599 / 88618925a7 / 88618925c5 / 8861892ec3
  23,965,728,038,725  (+1.7733%)  8861892599 / 88618925a7 / 88618925c7 / 8861892edd

CP-SAT raw status=OPTIMAL objective_value=23548137358244
CP-SAT chosen set == oracle optimum set: True
CP-SAT objective == oracle optimum:      True
```

**Recorded answers to the two asked questions:**

- **Oracle optimum value: `23,548,137,358,244`** (solver-scale integer).
- **The optimal facility set is UNIQUE** — exactly one of the 202 feasible
  full-service subsets attains it. The runner-up is `+0.5082%` away, so the optimum
  is strictly separated, not a knife-edge tie.

**NOTES**

- **The oracle is not as independent as its own docstring claims.** The docstring
  says it "deliberately re-derives the objective from the published contract rather
  than importing the model builder, so a defect in the model construction cannot
  hide by being shared with its own verifier." It then does exactly that import:

  ```python
  from services.zonepilot.optimization._cp_sat import FIXED_POINT, _normalisation_references
  ```

  `_cp_sat.py` *is* the model builder. The oracle independently re-derives the
  assignment rule, the P95 rollup, the feasibility test and the facility selection —
  which is the genuinely valuable part — but it shares the normalisation reference
  denominators with the thing it is certifying. A wrong denominator in
  `_normalisation_references` (e.g. `total_demand * horizon` for `p95_travel`) would
  be inherited by both and this test would still be green. **The certification covers
  "did CP-SAT find the best facility set under this objective", not "is this
  objective the right one."** That is a materially narrower claim than
  "independently certified" suggests, and it should be stated that way.
- Minor doc drift: the module docstring says "the feasible facility sets number only
  794." The true count for `sum(C(12,k)) for k=1..4` is **793** (12+66+220+495). The
  test itself only asserts `< 1_000`, so nothing fails; the prose is off by one.
- 591 of 793 subsets (74.5%) cannot serve all 94 zones within the 1800s cap. Full
  service is genuinely constraining, so the feasibility branch of the oracle is
  exercised rather than being dead code.
- `test_decision_is_reproducible_under_parallel_search` runs 5 CP-SAT solves at
  8 workers and gets one facility set, one assignment hash, one objective.
  Reproducible.

---

## CLAIM 3: the decision suite is stable, not flaky

**VERDICT: VERIFIED (for the sample size actually run — see notes)**

**COMMAND** (run three separate times, pinned HEAD verified before and after)

```
python -m pytest tests/decisions -q -p no:cacheprovider
```

**OUTPUT**

Pinned at `b035749`:

| Run | Result | Duration |
|---|---|---|
| 1 | `8 passed` | 46.40s |
| 2 | `8 passed` | 40.84s |
| 3 | `8 passed` | 39.56s |

I had also run the suite three times earlier in the session (before HEAD advanced):
`8 passed in 37.82s`, `8 passed in 38.20s`, `8 passed in 38.46s`. **6 for 6 overall,
zero failures, zero reruns, zero skips.**

The 8 tests:

```
test_decision_ledger.py::test_record_and_retrieve_decision
test_decision_ledger.py::test_decision_replay_verification
test_decision_ledger.py::test_shadow_evaluation_loop
test_decision_ledger.py::test_adversarial_pit_temporal_isolation
test_decision_ledger.py::test_pit_temporal_attack_and_artifact_corruption
test_policy_version_replay.py::test_policy_version_is_stamped_on_new_decisions
test_policy_version_replay.py::test_legacy_decision_is_not_replayed_under_the_current_policy
test_policy_version_replay.py::test_mismatched_policy_version_is_not_replayed
```

**NOTES**

- Durations are tightly clustered (39.6-46.4s at pin; the 46.4s was a cold first
  run). Tight clustering is a genuine positive signal — a flaky suite usually shows
  duration variance alongside intermittent failures.
- **3 runs is weak evidence for a non-flakiness claim.** A 1-in-20 flake has a ~86%
  chance of surviving 3 clean runs undetected. I can state "did not flake in 6
  consecutive runs"; I cannot state "is not flaky." If this claim gates a release,
  it needs a soak (50-100 runs) or `--count`-style repetition, not three passes.
- `pytest-rerunfailures` 16.5 is installed. It is **not** active here (no `--reruns`
  flag, no `addopts`), so these passes are first-attempt passes, not retried ones.
  Worth pinning: if `--reruns` is ever added to CI, this claim silently becomes
  unfalsifiable.
- The suite requires a live local Postgres at `TEST_DATABASE_URL`
  (`postgresql://postgres:postgres@127.0.0.1...`). Stability here is stability
  against one warm local database, not against CI infrastructure.

---

## CLAIM 4: objective components reconcile exactly to the solved objective

**VERDICT: VERIFIED — but the stated identity is a tautology; the load-bearing check is a different one**

**COMMAND** — independent real solve of the 94x12x3 problem, then direct comparison
of `sum(component.solver_scaled_contribution)` against
`objective.solver_objective_total` and against CP-SAT's own `objective_value`.

**OUTPUT**

```
--- objective components (n=5) ---
  expected_travel     raw=139117804000  solver_scaled=10,433,835,300,000  weighted=10,465,000
  p95_travel          raw=18869932      solver_scaled= 2,839,302,058,244  weighted= 2,839,000
  coverage_loss       raw=0             solver_scaled=             0      weighted=       0
  facility_cost       raw=4000          solver_scaled=10,000,000,000,000  weighted= 9,999,000
  failure_exposure    raw=2200          solver_scaled=   275,000,000,000  weighted=   275,000

  sum(solver_scaled_contribution) = 23,548,137,358,244
  objective.solver_objective_total = 23,548,137,358,244
  MATCH: True

  sum(weighted_contribution)       = 23,578,000
  objective.weighted_total         = 23,578,000
  MATCH: True

  CP-SAT raw status=OPTIMAL objective_value=23,548,137,358,244
  solver_objective_total == CP-SAT objective_value: True
```

**NOTES**

- The requested identity holds exactly, with no rounding slack.
- **However: `sum(component.solver_scaled_contribution) == objective.solver_objective_total`
  is true by construction and cannot fail.**
  `services/zonepilot/optimization/_cp_sat.py:638` literally reads:

  ```python
  solver_objective_total = sum(component.solver_scaled_contribution for component in components)
  ```

  Verifying that identity verifies a Python `sum()`. Presenting it as evidence that
  "components reconcile to the solved objective" overstates it.
- **The check that actually has content — and which I ran — is that this total equals
  CP-SAT's own `solver.objective_value`, a number produced by the solver rather than
  assembled by our reporting code.** It does: both are `23,548,137,358,244`, and both
  equal the exhaustive oracle optimum from Claim 2. That three-way agreement
  (reported total = CP-SAT internal objective = independent oracle) is real evidence
  and it is clean. The claim should be restated in those terms.
- Same caveat for the shipped test: `test_objective_components_reconcile_exactly`
  checks `weighted_contribution`/`weighted_total`, and also re-derives
  `normalized_basis_points` and `weighted_contribution` using the same formula the
  producer used. It is a self-consistency check, not an independent one.
- Observation on the objective's shape, not a defect: `facility_cost` contributes
  10.0e12 of the 23.5e12 total (42.5%) and `expected_travel` 10.4e12 (44.3%). Because
  `facility_cost` is normalised against *all 12* facilities' cost while only 4 open,
  the fixed-cost term is close to saturating its own reference. Whoever owns the
  weights should confirm 42.5% is intended.

---

## CLAIM 5: geography validation is non-vacuous

**VERDICT: VERIFIED — non-vacuousness proven two independent ways. But the validation's *scope* has a real hole; see notes.**

**COMMAND**

```
# 1. baseline
python -m pytest tests/geo/test_pilot_roads_lineage.py -q -p no:cacheprovider

# 2. inject Andorra under a Bengaluru name
cp data/geo/andorra-latest.osm.pbf data/geo/bengaluru_clip.osm.pbf
python -m pytest tests/geo/test_pilot_roads_lineage.py -v -p no:cacheprovider

# 3. restore
rm -f data/geo/bengaluru_clip.osm.pbf
python -m pytest tests/geo/test_pilot_roads_lineage.py -q -p no:cacheprovider
```

**OUTPUT**

Baseline (all 4 pass, nothing skipped, `osmium` present):

```
tests/geo/test_pilot_roads_lineage.py::test_pilot_roads_is_present_and_is_the_expected_artifact PASSED
tests/geo/test_pilot_roads_lineage.py::test_pilot_roads_coordinates_are_actually_in_bengaluru  PASSED
tests/geo/test_pilot_roads_lineage.py::test_no_artifact_named_bengaluru_contains_another_city   PASSED
tests/geo/test_pilot_roads_lineage.py::test_h3_network_cells_fall_inside_the_road_extract       PASSED
4 passed in 0.97s
```

With Andorra injected as `data/geo/bengaluru_clip.osm.pbf`
(sha256 `f7da0ba3...f2bb7`) — **FAILS as required**:

```
FAILED tests/geo/test_pilot_roads_lineage.py::test_no_artifact_named_bengaluru_contains_another_city
E  AssertionError: data\geo\bengaluru_clip.osm.pbf is the Andorra extract under a Bengaluru name
E  assert 'f7da0ba356d7ec1a...f067f2bb7' != 'f7da0ba356d7ec1a...f067f2bb7'
1 failed, 3 passed in 0.75s
```

After `rm -f data/geo/bengaluru_clip.osm.pbf` — **passes again, working tree clean**:

```
$ find data -name "*.osm.pbf"
data/geo/andorra-latest.osm.pbf
data/private/official/raw/osrm/pilot_roads.osm.pbf
$ git status --porcelain data/
(empty)
4 passed in 0.81s
```

**Second, stronger tamper (my own addition — the prescribed test only exercises the
SHA blocklist).** The copy test proves nothing about the coordinate assertions,
because it trips the hard-coded `ANDORRA_SHA256` compare and short-circuits before
`_osm_bounds` is ever called. So I re-encoded Andorra through
`osmium.SimpleWriter` into a **byte-different** file with an **unknown sha256**,
named `blr_reencoded_probe.osm.pbf` so it matches the `"blr"` token:

```
re-encoded probe sha256 = a7eccc42f84fe5db54403a50fdd755dd99925dc3dd511ec1039805f21c99e9fa
  == ANDORRA_SHA256? False   <- the hash blocklist CANNOT catch this file

FAILED test_no_artifact_named_bengaluru_contains_another_city
E  AssertionError: data\geo\blr_reencoded_probe.osm.pbf latitudes 42.3238052..42.7821915 are not Bengaluru
E  assert (12.7 <= 42.3238052 and 42.7821915 <= 13.2)
```

The coordinate check caught it on the data, with the hash defence bypassed. Probe
deleted; `git status --porcelain data/` empty; suite green again.

Real bounds read out of the actual artifacts:

| artifact | min_lat | max_lat | min_lon | max_lon | inside BLR window |
|---|---|---|---|---|---|
| `data/private/official/raw/osrm/pilot_roads.osm.pbf` | 12.84675 | 12.98803 | 77.50455 | 77.67687 | **yes** |
| `data/geo/andorra-latest.osm.pbf` | 42.32381 | 42.78219 | 1.29122 | 1.82465 | no |

**NOTES — three scope problems, two of them live in the tree right now**

1. **A Bengaluru-named routing graph in `data/geo/` is still substantially Andorra,
   and this test does not look at it.** The test only globs `*.osm.pbf`. It never
   inspects `.osrm*`. Comparing `data/geo/bengaluru_clip.osrm.*` against
   `data/geo/andorra-latest.osrm.*` file by file, **11 of 21 comparable files are
   byte-identical**, including the ones carrying actual geometry and labels:

   ```
   IDENTICAL: bengaluru_clip.osrm.geometry              (801,280 bytes)
   IDENTICAL: bengaluru_clip.osrm.nbg_nodes             (473,600 bytes)
   IDENTICAL: bengaluru_clip.osrm.names                 ( 22,016 bytes)
   IDENTICAL: bengaluru_clip.osrm.cnbg
   IDENTICAL: bengaluru_clip.osrm.turn_penalties_index
   IDENTICAL: bengaluru_clip.osrm.turn_duration_penalties
   IDENTICAL: bengaluru_clip.osrm.turn_weight_penalties
   IDENTICAL: bengaluru_clip.osrm.maneuver_overrides
   IDENTICAL: bengaluru_clip.osrm.ramIndex
   IDENTICAL: bengaluru_clip.osrm.restrictions
   IDENTICAL: bengaluru_clip.osrm.tls / .timestamp
   ```

   `bengaluru_clip.osrm` is also exactly 1,905,664 bytes — the same size as
   `andorra-latest.osrm`. This is the *same class of defect the test was written to
   prevent*, one directory over, in a different file extension, and the test is blind
   to it. It does not invalidate the pilot (the pilot reads
   `data/private/official/raw/osrm/pilot_roads.*`, which I confirmed is genuinely
   Bengaluru), but "geography validation is non-vacuous" must not be read as
   "no mislabelled geography remains in the repo." It does.

2. **`data/geo/bengaluru_clip.osm` is not OSM data at all.** It is 370 bytes of
   Apache HTML:

   ```
   <title>406 Not Acceptable</title>
   ... Apache/2.4.68 (Debian) Server at overpass-api.de Port 80
   ```

   A failed Overpass download was saved as if it were an extract and has been sitting
   there since Aug 8. No test looks at it.

3. **`_require_pilot_roads()` converts absence into a SKIP, and `*.pbf` is gitignored
   (`.gitignore:78`).** On a stock CI checkout the extract is absent, three of the
   four tests skip, and the suite reports green. The helper's own docstring argues
   this is better than the old silent `if path.exists():` — it is, because a skip is
   named in the report. But a skip still does not fail a build. **Unless CI treats
   skips in `tests/geo/` as failures, this suite provides zero protection on the
   runner that actually gates merges.** I verified it is non-vacuous *on this machine,
   where the artifact is mounted.* I cannot verify it is non-vacuous in CI, and the
   mechanism strongly suggests it is not. This helper landed mid-verification
   (commit `9d75c2c`).

---

## Summary

| # | Claim | Verdict | Hard number / evidence |
|---|---|---|---|
| 1 | 94-zone accounting: assigned + uncovered == 94 | **VERIFIED** | 13 passed. Real solve: assigned 94 + uncovered 0 = total 94, coverage 10000 bp, 282 assignments (94x3). Shipped test uses a synthetic dict, not a solve — I closed that gap myself. |
| 2 | Pilot optimum independently certified; CP-SAT == exhaustive oracle | **VERIFIED** (caveat) | 5 passed. Oracle optimum **23,548,137,358,244**; **unique** optimum; 202/793 subsets feasible; runner-up +0.5082%; CP-SAT matches value *and* set. Caveat: oracle imports `_normalisation_references` from the model builder it certifies. |
| 3 | Decision suite is stable, not flaky | **VERIFIED** for sample size | 8 passed x 6 consecutive runs (3 pinned: 46.40s / 40.84s / 39.56s). No reruns active. 3 runs is not a non-flakiness proof. |
| 4 | Objective components reconcile exactly to the solved objective | **VERIFIED** (restate it) | 23,548,137,358,244 three ways: component sum = CP-SAT `objective_value` = oracle. The literal stated identity is a tautology (`_cp_sat.py:638`); the CP-SAT comparison is the real evidence. |
| 5 | Geography validation is non-vacuous | **VERIFIED** on this machine | Byte-identical Andorra caught by SHA; **re-encoded** Andorra (sha `a7eccc42...`, blocklist bypassed) caught by coordinate bounds. Restored clean. But: `.osrm` graphs unchecked and 11/21 identical to Andorra; `bengaluru_clip.osm` is an HTTP 406 page; skips-not-fails on gitignored `*.pbf` likely makes it vacuous in CI. |

**Nothing was marked GREEN that I did not reproduce myself.** All five claims
reproduce. Four carry caveats that materially narrow what they establish:

- **Claim 2** certifies *optimality under the objective*, not *correctness of the
  objective* — the verifier shares denominators with the thing verified.
- **Claim 4** as literally stated cannot fail; its real content is the CP-SAT
  cross-check, which is sound.
- **Claim 3** is "did not flake in 6 runs," not "is not flaky."
- **Claim 5** is proven non-vacuous *here* and is genuinely well built (the
  coordinate check survived a tamper the hash check could not catch), but it is
  probably vacuous in CI, and there is an unrelated Andorra-under-Bengaluru artifact
  live in `data/geo/` right now that it does not look at.

**Process finding:** the branch advanced 5+ commits touching all files under test
while verification was in progress. Results here are pinned to `b035749`.

No source file under `services/`, `app/`, or `components/` was modified. The only
file written is this one. Both tamper probes were deleted and
`git status --porcelain data/` is empty.
