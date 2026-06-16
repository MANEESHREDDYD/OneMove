# Polyglot Architecture Report

OneMove has evolved from a pure Next.js application into a mature, multi-language marketplace intelligence platform.

## Architecture Components

- **TypeScript / Next.js**: Powers the product surface, UI/UX, and Server Actions.
- **SQL (Supabase/Postgres)**: Handles database persistence, RLS security, and Analytics Marts.
- **Python**: Manages data pipelines, ML scoring, model evaluation, and feature engineering.
- **Java**: Demonstrates an enterprise backend risk service (`java/onemove-risk-service`).
- **C**: Demonstrates a high-performance dispatch candidate ranking engine (`c/dispatch-engine`).

*Note: Java and C are optional portfolio subsystems. They are not required for the core localhost demo. They demonstrate how marketplace platforms split specialized workloads by language.*
