# OneMove CTO Demo Runbook

This document describes how to execute the OneMove Golden Path Demo (OPERATE → recommend → evidence → replay).

## Prerequisites
- Local Supabase instance running (`npx supabase start`)
- Node.js dependencies installed (`npm install`)
- Python environment activated (`uv sync`)

## Running the Demo (Automated)

The demo is driven by a Playwright end-to-end test that records the user journey while spawning a local Python solver worker in the background to fulfill optimization jobs deterministically.

To run the demo and generate the recording:

```bash
$env:ONEMOVE_DEMO_RECORD="1"
npx playwright test --config=onemove-demo.config.ts --project=record tests/e2e/operate-golden-path.spec.ts
```

The recorded `.webm` video will be saved to the `test-results/` directory.

## Golden Path Steps Demonstrated
1. **OPERATE**: Operator selects a region and requests an optimization.
2. **RECOMMEND**: The local solver calculates the optimal facility locations based on demand probabilities and commits the decision lineage to the ledger.
3. **EVIDENCE**: The UI presents the newly formed network structure, coverage metrics, and rationale for the decision.
4. **REPLAY**: The immutable decision is frozen in the PostgreSQL ledger, establishing cryptographic proof of the decision context.
