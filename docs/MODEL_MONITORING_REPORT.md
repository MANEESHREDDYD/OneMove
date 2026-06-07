# Model Monitoring & MLOps Report (Phase 4)

## Overview
OneMove's ML pipelines rely heavily on background scoring routines via CRON. To ensure observability, Phase 4 introduces a dedicated MLOps logging layer.

### ML Pipeline Run Tracking
Every execution of an ML script (such as `generate-demand-forecast.ts` or `score-merchant-reliability.ts`) is wrapped in a tracking abstraction (`logMlRun` in `scripts/ml/score-all.ts`). 

**Captured Metrics:**
- **Run Name & Family:** Identifies the specific model or heuristic script executing.
- **Timestamp & Duration:** Exact millisecond timing from start to termination.
- **Data Throughput:** Future-proofed schema columns for `input_row_count` and `output_row_count` to detect data drift or pipeline starvation.
- **Error Count & Status:** Strict `SUCCESS` or `FAILED` tagging for immediate alerting.

### Operations Dashboard
The MLOps interface at `/admin/mlops`:
- Serves as the central control plane for data science and engineering operators.
- Provides a summary of total runs, total errors, and throughput.
- Lists execution history chronologically with visual status indicators (Green/Red).
- Offers a synchronous trigger to re-run the entire scoring suite (`score-all.ts`) on demand.

### Technical Safeguards
Because executing heavy pipelines during a Next.js Server Action is inherently risky (due to Vercel/Next timeout limits), the UI triggers a detached `spawn` process for the pipeline, allowing the UI to return immediately and the pipeline to execute safely in the background.
