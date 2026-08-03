"""
Decision Core - Moteur de Decision Intelligence.

Package Python autonome pour l'import, la validation, le profiling,
la simulation et la génération de rapports statistiques.
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
