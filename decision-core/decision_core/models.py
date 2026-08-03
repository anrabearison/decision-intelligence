"""
Fichier de compatibilité pour decision_core.models.

Ce fichier réexporte toutes les classes depuis le nouveau package
decision_core/models pour préserver la rétrocompatibilité des imports.
"""
from decision_core.models import (
    SimulationConfig,
    AnalysisConfig,
    SimpleRegressionResult,
    LogisticRegressionResult,
    MultivariateRegressionResult,
    SimulationResult,
    AnomalyDetectionResult,
    DatasetSummary,
    ExploitabilityScore,
    ReportResult,
)

__all__ = [
    "SimulationConfig",
    "AnalysisConfig",
    "SimpleRegressionResult",
    "LogisticRegressionResult",
    "MultivariateRegressionResult",
    "SimulationResult",
    "AnomalyDetectionResult",
    "DatasetSummary",
    "ExploitabilityScore",
    "ReportResult",
]
