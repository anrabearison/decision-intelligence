"""
Package de statistiques pour decision-core.

Ce package regroupe les fonctions de profiling, de régression,
de détection d'influence, de détection de colonnes dérivées et de traitement catégoriel.
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
from decision_core.stats.categorical import (
    encode_categorical_features,
    detect_significant_subgroups,
    generate_segmented_reports,
)
from decision_core.stats.distribution import (
    detect_count_data_distribution,
    detect_zero_inflation,
    detect_heavy_tail,
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
    # Categorical
    "encode_categorical_features",
    "detect_significant_subgroups",
    "generate_segmented_reports",
    # Distribution
    "detect_count_data_distribution",
    "detect_zero_inflation",
    "detect_heavy_tail",
]
