# Load Testing & Performance Report

## Execution Context
- Tool: `autocannon` / `playwright`
- Target: `http://localhost:3000`
- Parameters: 10 connections, 10s duration

## Results
- **Req/Sec**: ~4,500
- **Errors**: 45,000 non-2xx responses were detected during the raw autocannon run.
- **Latency**: Sub-3ms (due to immediate crash/rejection).

### Playwright Concurrency Stress
During the execution of 144 E2E tests using 8 workers across 4 browsers concurrently, the Next.js development server threw multiple `ECONNRESET` and `Target page, context or browser has been closed` errors. 

### Bottlenecks Identified
- Next.js development server is unoptimized for mass concurrent writes and navigations.
- The Admin Command Center query latency spikes under load, although it is currently mitigated by the fact that RLS blocks the admin queries from returning massive datasets.

### Recommendations
- Run the production build (`npm run build && npm start`) before conducting final load tests.
- Paginate the Admin Command Center queries instead of pulling the entire `orders` table.
