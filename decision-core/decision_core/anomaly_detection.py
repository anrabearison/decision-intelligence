"""
Fichier de compatibilité pour decision_core.anomaly_detection.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.quality pour préserver la rétrocompatibilité des imports.
"""
from decision_core.quality.anomaly_detection import detect_anomalies_iqr, MIN_RELIABLE_SAMPLE_SIZE

__all__ = [
    "detect_anomalies_iqr",
    "MIN_RELIABLE_SAMPLE_SIZE",
]

