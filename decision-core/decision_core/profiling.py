"""
Fichier de compatibilité pour decision_core.profiling.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.stats pour préserver la rétrocompatibilité des imports.
"""
from decision_core.stats.profiling import (
    descriptive_stats,
    legitimate_numeric_columns,
    correlation_matrix,
    correlation_pvalues,
    MAX_COLUMNS_FOR_CORRELATION,
)

__all__ = [
    "descriptive_stats",
    "legitimate_numeric_columns",
    "correlation_matrix",
    "correlation_pvalues",
    "MAX_COLUMNS_FOR_CORRELATION",
]
