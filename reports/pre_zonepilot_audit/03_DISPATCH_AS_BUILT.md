# 03 DISPATCH AS BUILT

## CURRENT IMPLEMENTATION
The C-based dispatch engine (`c/dispatch-engine/`) executes a simple O(N) Haversine nearest-neighbor search. It loops through an array of partners and selects the closest geographical point. It does **not** implement bipartite matching, min-cost flow, or Hungarian assignment. It does not natively support complex time windows, capacity, or repositioning out-of-the-box in the core solver loop.

## CLASSIFICATION
**SIMULATED_DEMO** (Algorithmically) / **VERIFIED_WORKING** (Execution)

## WHAT IS DEMO
The algorithmic claims of "full bipartite optimization" and "dispatch optimization". The solver merely finds the closest coordinate point. The benchmark size and simulated constraints do not accurately model real marketplace physics.

## WHAT IS REAL
The C code actually compiles, runs, and correctly executes a Haversine nearest-neighbor calculation over the data provided.

## WHAT IS CONNECTED
**CODE_PRESENT_UNINTEGRATED** / **DEAD_OR_ORPHANED**
The Next.js core application does not natively send real-time job arrays to this C-engine over a running socket/FFI in production.

## WHAT ZONEPILOT CAN REUSE
**REUSE_PATTERN_ONLY** / **QUARANTINE**
The architectural scaffolding (Makefile, data ingestion pattern) is usable, but the actual dispatch logic is far too primitive for ZonePilot. The current implementation must be quarantined to prevent simplistic nearest-neighbor results from contaminating experimental metrics.

## WHAT MUST BE REPLACED
The entire matching algorithm must be replaced with a true assignment optimizer (e.g., OR-Tools, network flow, or Hungarian algorithm) to handle batching, constraints, and bipartite matching.
