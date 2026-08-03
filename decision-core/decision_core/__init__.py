"""
Decision-Core - Moteur d'analyse de données pour la prise de décision.

Ce package fournit des outils pour :
- Régression (linéaire, logistique, multivariée)
- Traitement des variables catégorielles (encodage one-hot, détection de sous-groupes)
- Détection d'anomalies et d'influence
- Profiling des données (statistiques, corrélations)
- Simulation de scénarios
- Génération de rapports (texte et HTML)

Nouveautés P0 :
- Régression logistique automatique pour cibles binaires
- Détection de facteurs confondants
- Avertissements de causalité systématiques

Nouveautés P1.1 :
- Encodage one-hot automatique des variables catégorielles
- Détection de sous-groupes significatifs via eta-carré
- Rapports segmentés par sous-groupes

Exemple d'utilisation :
    >>> from decision_core import import_file, fit_simple_regression, generate_report
    >>> df = import_file("data.csv")
    >>> model = fit_simple_regression(df, target="Y", feature="X")
    >>> report = generate_report(df, config)
"""

from decision_core.io.importer import import_file, UnsupportedFileFormatError
from decision_core.quality.validation import validate_dataset
from decision_core.quality.type_detection import detect_column_type, is_identifier_column
from decision_core.stats.profiling import (
    descriptive_stats,
    legitimate_numeric_columns,
    correlation_matrix,
    correlation_pvalues,
    MAX_COLUMNS_FOR_CORRELATION,
)
from decision_core.quality.anomaly_detection import detect_anomalies_iqr, MIN_RELIABLE_SAMPLE_SIZE
from decision_core.stats.regression import (
    fit_simple_regression,
    fit_multivariate_regression,
    fit_logistic_regression,
    is_binary_target,
    detect_confounders,
    InsufficientDataError,
)
from decision_core.stats.categorical import (
    encode_categorical_features,
    detect_significant_subgroups,
    generate_segmented_reports,
)
from decision_core.stats.influence_detection import compute_cooks_distance, detect_influential_points
from decision_core.simulation import simulate_scenario
from decision_core.reporting import generate_report, render_text_summary, render_html
from decision_core.stats.derived_columns import detect_derived_relationships
from decision_core.models import (
    SimulationConfig,
    SimulationResult,
    AnalysisConfig,
    SimpleRegressionResult,
    MultivariateRegressionResult,
    AnomalyDetectionResult,
    DatasetSummary,
    ExploitabilityScore,
    ReportResult,
)

__all__ = [
    # Importer
    "import_file",
    "UnsupportedFileFormatError",
    # Validation
    "validate_dataset",
    # Type detection
    "detect_column_type",
    "is_identifier_column",
    # Profiling
    "descriptive_stats",
    "legitimate_numeric_columns",
    "correlation_matrix",
    "correlation_pvalues",
    "MAX_COLUMNS_FOR_CORRELATION",
    # Anomaly detection
    "detect_anomalies_iqr",
    "MIN_RELIABLE_SAMPLE_SIZE",
    # Regression
    "fit_simple_regression",
    "fit_multivariate_regression",
    "fit_logistic_regression",
    "is_binary_target",
    "detect_confounders",
    "InsufficientDataError",
    # Categorical
    "encode_categorical_features",
    "detect_significant_subgroups",
    "generate_segmented_reports",
    # Influence detection
    "compute_cooks_distance",
    "detect_influential_points",
    # Simulation
    "simulate_scenario",
    # Report
    "generate_report",
    "render_text_summary",
    "render_html",
    # Derived columns
    "detect_derived_relationships",
    # Models
    "SimulationConfig",
    "SimulationResult",
    "AnalysisConfig",
    "SimpleRegressionResult",
    "MultivariateRegressionResult",
    "AnomalyDetectionResult",
    "DatasetSummary",
    "ExploitabilityScore",
    "ReportResult",
]
