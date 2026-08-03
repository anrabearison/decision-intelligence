"""
Fichier de compatibilité pour decision_core.validation.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.quality pour préserver la rétrocompatibilité des imports.
"""
from decision_core.quality.validation import validate_dataset

__all__ = [
    "validate_dataset",
]
