# OneMove — Executive Overview

**Status:** pilot-stage system, Bengaluru. Branch `hotfix/onemove-p0-security-incident` at
`b035749`. This document describes what exists, and is explicit about what does not.

---

## The decision problem

A company that moves physical goods through a city has to commit capacity to locations
before it knows what the demand will be. Where do the dark stores go. Which depots stay
open through monsoon season. Where does a new hub sit so that service holds when the Outer
Ring Road backs up.

These decisions share an uncomfortable shape. They are expensive — a facility is a lease, a
fit-out, and a hiring plan. They are slow to reverse — the cost of being wrong is paid over
quarters, not days. And they are made against a network that does not hold still: travel
times swing with congestion, weather, and single-point road closures, and the swing is not
symmetric. A placement that looks efficient on average travel time can be the placement that
fails hardest in the tail, which is exactly when service level is visible to customers.

The pain is not that the decision is hard to compute. It is that the decision is hard to
**defend**. Six months later, someone asks why capacity sits where it sits. By then the
spreadsheet has been edited, the analyst has moved teams, the traffic data has been
overwritten with newer traffic data, and nobody can reconstruct what was actually known on
the day the decision was made. The organisation cannot tell the difference between a
decision that was wrong and a decision that was reasonable given the information available.

## How teams handle this today

Three patterns, each with a characteristic failure.

**The spreadsheet.** Average travel times, a coverage radius, a gut-feel cost per site. It is
fast, everyone can read it, and it is the honest baseline for most teams. It cannot represent
tail behaviour, so it systematically under-weights the scenarios that hurt. And it carries no
record of its own inputs — the cells get overwritten.

**The consulting study.** A network study produces a defensible recommendation with real
analysis behind it. It is a photograph. It is accurate on the day it is delivered and
degrades from then on, it costs six figures to refresh, and the model that produced it
usually does not stay in the company.

**The internal optimizer.** A data science team builds a solver. It answers the question and
often answers it well. But the assumptions live in code, the inputs are whatever the database
held at run time, and the output is a recommendation with no attached record of what produced
it. When it is challenged, the honest answer is "we would have to re-run it", and re-running
it against today's data does not answer a question about a decision made in March.

The common gap is not optimization. It is that none of these produce a decision that can be
audited against its own moment in time.

## What OneMove does

OneMove takes a city network, a set of candidate facility locations, and a set of explicitly
declared assumptions, and produces a placement decision that can be re-derived later from the
same inputs.

Three properties carry the weight:

**Every number states what kind of number it is.** A road length measured from OpenStreetMap,
a travel time computed by a routing engine, a scenario probability someone chose, and a
figure typed in by an operator are four different kinds of claim. The system labels each one
with an evidence class and never lets one borrow the authority of another. A value that does
not exist is reported as unavailable — with a reason — rather than defaulted to zero. This
sounds like bookkeeping. It is the reason the other two properties mean anything.

**A decision is frozen.** When a solver result is accepted, the system records the result,
the input snapshot, the digest of the assumption set, the code version, and the policy
version together as one immutable record, with an evidence chain linking every node back to
its source. An operator cannot type plausible-looking metrics and have them stored as solver
output; caller-supplied figures are kept separately and labelled unverified.

**A frozen decision can be replayed at its own decision time.** The system re-derives the
decision using only information that existed at or before the moment it was made. Forecasts
and observations issued afterwards are invisible to the replay. The verdict is computed, not
stored: the frozen hash and the recomputed hash are both shown, and a mismatch is reported as
drift rather than quietly hidden.

That last property is the one that answers the question the other three approaches cannot:
*what did we know, and would the same information produce the same answer?*

## A concrete example

The pilot covers a bounded area of Bengaluru — 94 hexagonal cells (H3 resolution 8) built
from a public OpenStreetMap road extract of 11,285 drivable ways over named Bengaluru
arterials.

Each cell carries its road length, intersection count, and commercial POI count, all measured
from that public extract. The demand signal is built from those counts. **It is a geographic
proxy for where commercial activity is, not a record of orders**, and the system labels it as
such everywhere it appears.

From those 94 cells, the twelve with the highest commercial POI counts become candidate
facility sites. The optimizer chooses at most four to open, and assigns every one of the 94
cells to an open facility. It evaluates each candidate configuration across three scenarios:
free-flow travel at 60% weight, a 1.4× travel-time inflation at 30%, and a 1.6× inflation at
10%. Those three probabilities are a declared judgement, not a measured distribution, and
they are recorded as assumptions with written rationale.

The solver — Google OR-Tools CP-SAT — returned a proven optimal answer covering all 94 cells,
in roughly eight seconds, five times in a row, producing an identical facility set and
objective each time. The result was independently checked by brute force: enumerating all 793
permitted facility combinations takes 0.08 seconds and agrees with the solver exactly.

The resulting decision carries an eight-node evidence chain — decision, solver result, input
snapshot, travel matrix, road network, assumption set, release identity — and replays to an
exact hash match.

The useful part of that example is not the eight seconds. It is that a reader can see which
line is measured public geography, which line is a routing computation, and which line is a
number a human chose, without having to trust the summary.

## What is real, what is simulated, what is assumed

**Real, and verified.** The Bengaluru geography: 94 H3 resolution-8 cells, all confirmed to
fall inside the road extract by coordinate check rather than by filename. The road network
and the routing graph built from it. The CP-SAT optimization — a genuine solve, independently
certified against an exhaustive oracle. The decision freeze, the evidence chain, and the
point-in-time replay, each demonstrated end to end with real identifiers.

**Simulated, and labelled.** Every disruption. Heavy rain, corridor cuts, and travel-time
inflation are counterfactuals applied to the authentic baseline. The scenario classification
is structural, not editable through the assumption registry, so a simulation cannot be
relabelled as an observation.

**Assumed, and sealed.** The economics and the scenario weights. Demand weighting per POI,
cost per facility, the three scenario probabilities. These live in a digest-sealed assumption
set (`r1-pilot-proxy@1.0.0`), each with a written rationale, and every one is reachable from
the decision record. They are declared proxies. Nobody has measured them.

**Not real, and this is the important line.** Traffic and weather are not flowing. Collectors
for both exist as working code, but nothing schedules them, and the observation tables are
empty. Any live-looking traffic or weather figure shown in a demo was fetched by a script at
recording time and baked in. OneMove today is a decision system running on public geography
and declared assumptions — not a live telemetry platform.

## Architecture in brief

A web frontend for operators, a Python API, a PostgreSQL database of record, and an
optimization worker that consumes jobs from a queue and writes results back. Optimization
runs asynchronously because a solve takes seconds, not milliseconds. Infrastructure is
defined as code for two cloud environments.

The part worth an executive's attention is not the stack. It is that the database is a ledger
rather than a cache: decisions, evidence chains, and assumption sets are written to be read
back months later, and the replay path reads them under a time constraint rather than
reading current state.

## Current limitations

Stated plainly, because a pilot evaluated on an inflated description fails later and more
expensively.

- **No live data ingestion.** Traffic and weather collectors are not scheduled; the
  observation tables are empty.
- **No backtest.** Decision quality has never been evaluated against realised outcomes. There
  is no historical archive identified to test against.
- **No do-nothing baseline.** The system reports what it chose, but not whether that beats
  changing nothing — which is the first question any operator will ask.
- **No plain-language explanation of a decision.** The objective components are recorded, but
  there is no human-facing account of which constraint bound and why a given site opened.
- **The map is not interactive.** It is a pre-rendered image with an overlay. No pan, no zoom.
- **One city.** Bengaluru is embedded in the domain configuration. Multi-city is unbuilt work,
  not a setting.
- **No measured scale limits.** No load, soak, or chaos testing has been run.
- **An open security incident.** A database credential was exposed in a public repository.
  Containment is complete — the code path that caused it is fixed, CI is isolated from
  production, and secret scanning gates every build — but the credential is in git history and
  the incident stays open until it is rotated in the provider console. That rotation is an
  owner action, not an engineering one.
- **The default branch is not the product.** The working system is 85 commits ahead of `main`.
  Anyone evaluating this by cloning the default branch will see an older system.
- **No cost model and no provider licensing review** for the map and data providers yet. Both
  are required before commercial deployment.

## Pilot path

The gaps above sort into a defensible order.

**Before any pilot can be credible.** Rotate the exposed credential and close the incident.
Merge the working branch so the default branch is the product. Schedule the traffic and
weather collectors so observations actually accumulate — this is the single change that moves
the system from public-geography-only to live, and it is a scheduling and operations task,
not new modelling.

**Before an operator will trust an answer.** Add the do-nothing baseline, so every
recommendation is stated as a delta against changing nothing. Add the structured
why-this-decision record, so the answer can be argued with. Expose the sensitivity analysis
that already exists in code but has no route to reach it — an operator needs to know which
assumption the answer is fragile to.

**Before the decisions can be claimed to be good.** Accumulate enough observation history to
run a real backtest, then evaluate frozen decisions against what actually happened. Until
that exists, the honest claim is that OneMove produces decisions that are *reproducible and
auditable*, not decisions that are *proven better*. Those are different claims and only the
first one is currently supported.

**Before it is a product rather than a pilot.** Replace the static map with a real
interactive one. Complete the licensing and cost review. Move the city out of domain
constants into configuration. Measure the scale limits rather than assuming them.

The reason to run the pilot before all of that is finished is that the auditability
machinery — evidence classes, decision freeze, point-in-time replay — is the part that is
hardest to retrofit and it is already built and demonstrated. The remaining work is data
plumbing, explanation surfaces, and validation. That is a more tractable list than the one it
replaces.

---

**Further reading.** [`README.md`](../README.md) for the technical description.
[`docs/audit/CTO_REVIEW_BASELINE.md`](audit/CTO_REVIEW_BASELINE.md) for the subsystem-level
audit with evidence. [`docs/readiness/readiness_matrix.yaml`](readiness/readiness_matrix.yaml)
for per-requirement status. [`docs/readiness/failure_ledger.jsonl`](readiness/failure_ledger.jsonl)
for what was found broken and what was done about it.
