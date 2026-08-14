# 04 INTELLIGENCE AS BUILT

## OVERVIEW
An audit of the Python machine learning module (`python/src/onemove_intelligence/`) and TypeScript ML scripts (`scripts/ml/`).

## CLASSIFICATION
**SIMULATED_DEMO**

## PYTHON DATA/ML AUDIT FINDINGS

### Model State
- **Classification**: **synthetic generator** / **random simulation**
- The Python ML models are completely synthetic and deterministic. They are **not trained** statistical models.

### Implementations
- **`demand_forecast.py`**: Uses a hardcoded sine wave with static seeded noise (`np.random.seed(42)`) to generate forecasts. It is a deterministic rule system/synthetic generator, not a predictive model trained on marketplace history.
- **`dispatch_optimizer.py`**: Creates random coordinates for a mock distance matrix rather than optimizing actual spatial data.
- **`scripts/ml/run-dispatch-simulation.ts`**: Fetches real DB entities but injects random candidate attributes.

### DATA CONTAMINATION RISK
**P0 - SYNTHETIC DATA CONTAMINATION RISK**
The "predictions" and "forecasts" are synthetic. This must be strictly isolated from ZonePilot. If ZonePilot consumes this demand forecast, the experimental environment will be modeling a hardcoded sine wave rather than true counterfactual marketplace dynamics.

## ZONEPILOT REUSE
**QUARANTINE** / **REPLACE**
The intelligence module acts as a mock simulation. The orchestration and CLI scaffolding (`cli.py`) can be reused (**REUSE_WITH_EXTENSION**), but the actual algorithms must be entirely replaced with real data science models.
