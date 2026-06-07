# Experimentation Platform Report (Phase 4)

Phase 4 Status: GO for private localhost portfolio review after validation.
Production Status: NOT YET APPROVED.


## Architecture
The A/B testing and experimentation platform provides deterministic routing and analytical tracking without impacting synchronous rendering performance.

### Key Components
1. **Experiment Engine (`lib/experiments/experimentEngine.ts`)**: Core logic for registering experiments, checking assignment, and logging metrics.
2. **Assignment Logic (`lib/experiments/assignment.ts`)**: Uses MD5 hashing (`crypto.createHash('md5')`) on a combination of `userId` and `experimentId` to ensure a given user consistently maps to the same variant bucket deterministically, bypassing the need for sticky session cookies or stateful lookups.
3. **Metrics Tracking**: `experiment_metrics` table aggregates impressions, conversions, and revenue using safe SQL upserts with a `(experiment_id, variant_id)` unique constraint.

### Admin Dashboard
Located at `/admin/experiments`, it allows product operators to:
- View all active A/B tests (e.g., Surge Pricing UI, Dynamic ETA vs Static ETA).
- Review aggregate allocations (Control vs Treatment).
- Observe conversion rates and revenue impact.
- Access an automated deterministic recommendation engine (e.g., `continue (winning)`, `stop (underperforming)`).

### Integration
The experimentation engine is designed to be called server-side during Next.js rendering, logging impressions asynchronously to prevent blocking the critical path.
