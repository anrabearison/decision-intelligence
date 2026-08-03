"""
Package de qualité pour decision-core.

Ce package regroupe les fonctions de validation, de détection de type
et de détection d'anomalies pour assurer la qualité des données.
"""
from decision_core.quality.validation import validate_dataset
from decision_core.quality.anomaly_detection import detect_anomalies_iqr, MIN_RELIABLE_SAMPLE_SIZE
from decision_core.quality.type_detection import detect_column_type, is_identifier_column

__all__ = [
    "validate_dataset",
    "detect_anomalies_iqr",
    "MIN_RELIABLE_SAMPLE_SIZE",
    "detect_column_type",
    "is_identifier_column",
]
