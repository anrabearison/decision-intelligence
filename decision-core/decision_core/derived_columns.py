"""
Fichier de compatibilité pour decision_core.derived_columns.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.stats pour préserver la rétrocompatibilité des imports.
"""
from decision_core.stats.derived_columns import (
    detect_derived_relationships,
    MAX_COLUMNS_FOR_DERIVED_DETECTION,
)

__all__ = [
    "detect_derived_relationships",
    "MAX_COLUMNS_FOR_DERIVED_DETECTION",
]
