"""
Fichier de compatibilité pour decision_core.influence_detection.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.stats pour préserver la rétrocompatibilité des imports.
"""
from decision_core.stats.influence_detection import (
    compute_cooks_distance,
    detect_influential_points,
    DEFAULT_THRESHOLD_RATIO,
)

__all__ = [
    "compute_cooks_distance",
    "detect_influential_points",
    "DEFAULT_THRESHOLD_RATIO",
]
