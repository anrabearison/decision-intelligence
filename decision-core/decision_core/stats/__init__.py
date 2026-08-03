"""
Package de statistiques pour decision-core.

Ce package regroupe les fonctions de profiling, de régression,
de détection d'influence et de détection de colonnes dérivées.
"""
from decision_core.stats.profiling import (
    descriptive_stats,
    legitimate_numeric_columns,
    correlation_matrix,
    correlation_pvalues,
    MAX_COLUMNS_FOR_CORRELATION,
)
from decision_core.stats.regression import (
    fit_simple_regression,
    fit_multivariate_regression,
    fit_logistic_regression,
    is_binary_target,
    detect_confounders,
    validate_regression_inputs,
    InsufficientDataError,
    MIN_ROWS_FOR_REGRESSION,
)
from decision_core.stats.influence_detection import (
    compute_cooks_distance,
    detect_influential_points,
    DEFAULT_THRESHOLD_RATIO,
)
from decision_core.stats.derived_columns import (
    detect_derived_relationships,
    MAX_COLUMNS_FOR_DERIVED_DETECTION,
)

__all__ = [
    # Profiling
    "descriptive_stats",
    "legitimate_numeric_columns",
    "correlation_matrix",
    "correlation_pvalues",
    "MAX_COLUMNS_FOR_CORRELATION",
    # Regression
    "fit_simple_regression",
    "fit_multivariate_regression",
    "fit_logistic_regression",
    "is_binary_target",
    "detect_confounders",
    "validate_regression_inputs",
    "InsufficientDataError",
    "MIN_ROWS_FOR_REGRESSION",
    # Influence detection
    "compute_cooks_distance",
    "detect_influential_points",
    "DEFAULT_THRESHOLD_RATIO",
    # Derived columns
    "detect_derived_relationships",
    "MAX_COLUMNS_FOR_DERIVED_DETECTION",
]
