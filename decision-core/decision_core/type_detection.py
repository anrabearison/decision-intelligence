"""
Fichier de compatibilité pour decision_core.type_detection.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.quality pour préserver la rétrocompatibilité des imports.
"""
from decision_core.quality.type_detection import detect_column_type, is_identifier_column

__all__ = [
    "detect_column_type",
    "is_identifier_column",
]
