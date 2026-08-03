"""
Modèles de données typés pour decision-core.

Ce package regroupe les dataclasses de configuration et de résultats
pour la simulation, la régression, la détection d'anomalies et les rapports.
"""
from decision_core.models.config import SimulationConfig, AnalysisConfig
from decision_core.models.regression import SimpleRegressionResult, MultivariateRegressionResult
from decision_core.models.simulation import SimulationResult
from decision_core.models.anomaly import AnomalyDetectionResult
from decision_core.models.report import DatasetSummary, ExploitabilityScore, ReportResult

__all__ = [
    # Configuration
    "SimulationConfig",
    "AnalysisConfig",
    # Regression results
    "SimpleRegressionResult",
    "MultivariateRegressionResult",
    # Simulation result
    "SimulationResult",
    # Anomaly detection result
    "AnomalyDetectionResult",
    # Report models
    "DatasetSummary",
    "ExploitabilityScore",
    "ReportResult",
]
