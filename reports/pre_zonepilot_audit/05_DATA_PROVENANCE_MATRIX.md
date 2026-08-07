# 05 DATA PROVENANCE MATRIX

## Assessment: SYNTHETIC & DETERMINISTIC_SEED Heavily Dominant

### 1. Organic Data (`REAL_DATABASE_OPERATION`)
- **Presence**: Minimal. 
- **Usage**: Only generated when a user manually interacts with the UI in the current session (e.g., booking a new ride or updating a profile). 
- **Classification**: **REAL_USER_GENERATED**

### 2. Generated Data (`SYNTHETIC` & `DETERMINISTIC_SEED`)
- **Presence**: Pervasive.
- **Implementation**: The repository uses robust seed scripts (`scripts/generate-production-demo-data.ts`) utilizing `@faker-js/faker`.
- **Methodology**: 
  - Seeds enforce invariants across 500+ products, 200+ orders, payments, and ML logs.
  - Data generation scripts are designed to wipe and regenerate the `is_demo = true` flags to provide a clean slate for demonstrations.
  - Scenarios (e.g., "High demand dinner rush", "Low-performing partner") are injected artificially as metadata into orders and ML score logs.

### 3. Analytics & Demand Heatmaps
- **Presence**: **FAKER_GENERATED** / **DERIVED**
- The live demand heatmaps and merchant analytics operate on seeded demo records. They are not pulling organic live event pipelines.
