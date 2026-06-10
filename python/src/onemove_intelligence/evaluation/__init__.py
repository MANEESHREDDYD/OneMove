"""Model evaluation package for OneMove Intelligence.

Provides deterministic, reproducible offline evaluation metrics for the
forecasting, dispatch, risk, recommendation, segmentation, merchant-reliability
and partner-trust models that power the OneMove admin intelligence surfaces.
"""

from onemove_intelligence.evaluation.model_evaluation import evaluate_models

__all__ = ["evaluate_models"]
