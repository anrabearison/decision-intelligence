"""
Fichier de compatibilité pour decision_core.regression.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.stats pour préserver la rétrocompatibilité des imports.
"""
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

__all__ = [
    "fit_simple_regression",
    "fit_multivariate_regression",
    "fit_logistic_regression",
    "is_binary_target",
    "detect_confounders",
    "validate_regression_inputs",
    "InsufficientDataError",
    "MIN_ROWS_FOR_REGRESSION",
]
