"""
Contexte de construction de rapport pour decision-core.

Ce module définit la structure de contexte utilisée lors de la génération
du rapport pour réduire la complexité de generate_report().
"""
from dataclasses import dataclass, field
from typing import Any
import pandas as pd
from decision_core.models import SimulationConfig, AnalysisConfig


@dataclass
class ReportBuildContext:
    """Contexte de construction du rapport d'analyse.
    
    Contient toutes les données intermédiaires nécessaires à la construction
    du rapport, réduisant ainsi le nombre de paramètres passés entre les
    fonctions de génération.
    """
    df: pd.DataFrame
    typed_simulation: SimulationConfig | None
    typed_analysis: AnalysisConfig
    warnings: list[str]
    n_rows: int
    
    # Validation et profiling
    validation: dict[str, Any] | None = None
    numeric_cols: list[str] = field(default_factory=list)
    profiling: dict[str, Any] = field(default_factory=dict)
    
    # Anomalies
    anomalies: dict[str, Any] = field(default_factory=dict)
    
    # Corrélations
    derived_relationships: set[frozenset[str]] = field(default_factory=set)
    top_correlations: list[dict[str, Any]] = field(default_factory=list)
    corr_pairs: list[dict[str, Any]] = field(default_factory=list)
    
    # Sous-groupes et non-linéarité
    significant_subgroups: list[dict[str, Any]] = field(default_factory=list)
    nonlinearity_patterns: list[Any] = field(default_factory=list)
    excluded_columns: set[str] = field(default_factory=set)
    
    # Simulation
    simulation: dict[str, Any] | None = None

    # Insight principal
    main_insight: str | None = None

    # Warnings structurés
    warnings_structured: list[dict[str, Any]] = field(default_factory=list)

    # Score d'exploitabilité
    exploitability: Any = None
