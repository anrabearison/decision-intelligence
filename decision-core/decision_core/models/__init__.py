"""
Package de modèles pour decision-core.

Ce package contient les dataclasses pour les configurations et résultats.
"""
from decision_core.models.config import SimulationConfig, AnalysisConfig
from decision_core.models.regression import (
    SimpleRegressionResult,
    LogisticRegressionResult,
    MultivariateRegressionResult,
)
from decision_core.models.simulation import SimulationResult
from decision_core.models.anomaly import AnomalyDetectionResult
from decision_core.models.report import DatasetSummary, ExploitabilityScore, ReportResult
from decision_core.models.nonlinearity import QuadraticPatternResult, StepPatternResult
from decision_core.models.distribution import (
    CountDataDistributionResult,
    ZeroInflatedDistributionResult,
    HeavyTailDistributionResult,
)

__all__ = [
    # Config
    "SimulationConfig",
    "AnalysisConfig",
    # Regression results
    "SimpleRegressionResult",
    "LogisticRegressionResult",
    "MultivariateRegressionResult",
    # Other results
    "SimulationResult",
    "AnomalyDetectionResult",
    "ReportResult",
    "DatasetSummary",
    "ExploitabilityScore",
    # Nonlinearity results
    "QuadraticPatternResult",
    "StepPatternResult",
    # Distribution results
    "CountDataDistributionResult",
    "ZeroInflatedDistributionResult",
    "HeavyTailDistributionResult",
]
