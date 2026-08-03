"""
Construction du rapport pour decision-core.
"""
import pandas as pd
from decision_core.quality.validation import validate_dataset
from decision_core.stats.profiling import (
    descriptive_stats,
    correlation_pvalues,
    legitimate_numeric_columns,
)
from decision_core.stats.derived_columns import detect_derived_relationships
from decision_core.stats.regression import detect_confounders
from decision_core.stats.categorical import detect_significant_subgroups
from decision_core.quality.anomaly_detection import detect_anomalies_iqr
from decision_core.simulation import simulate_scenario
from decision_core.models import (
    SimulationConfig,
    AnalysisConfig,
    DatasetSummary,
    ReportResult,
)
from decision_core.reporting.scoring import _compute_exploitability_score
from decision_core.reporting.warnings import (
    _build_seasonality_warnings,
    _build_correlation_warnings,
    _build_simulation_warnings,
    _build_nonlinearity_warnings,
)
from decision_core.reporting.scoring import SMALL_SAMPLE_THRESHOLD


def _normalize_configs(
    simulation_config: SimulationConfig | dict | None,
    analysis_config: AnalysisConfig | dict | None,
) -> tuple[SimulationConfig | None, AnalysisConfig]:
    """Normalise les configurations : accepte dict ou dataclass, retourne dataclass.

    Args:
        simulation_config: Configuration de simulation typée ou dict.
        analysis_config: Configuration d'analyse typée ou dict.

    Returns:
        Tuple (typed_simulation, typed_analysis) avec les configurations normalisées.
    """
    if isinstance(analysis_config, AnalysisConfig):
        typed_analysis = analysis_config
    elif isinstance(analysis_config, dict):
        typed_analysis = AnalysisConfig.from_mapping(analysis_config)
    else:
        typed_analysis = AnalysisConfig()

    typed_simulation: SimulationConfig | None = None
    if isinstance(simulation_config, SimulationConfig):
        typed_simulation = simulation_config
    elif isinstance(simulation_config, dict):
        typed_simulation = SimulationConfig.from_mapping(simulation_config)

    return typed_simulation, typed_analysis


def _build_anomalies_section(
    df: pd.DataFrame,
    numeric_cols: list[str],
    iqr_k: float,
) -> dict:
    """Détecte les anomalies IQR par colonne numérique.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        iqr_k: Multiplicateur IQR pour la détection.

    Returns:
        Dictionnaire des anomalies par colonne.
    """
    anomalies: dict = {}
    for col in numeric_cols:
        result = detect_anomalies_iqr(df[col], k=iqr_k)
        if result.indices and result.reliable:
            anomalies[col] = result.to_dict()
    return anomalies


def _build_correlations_section(
    df: pd.DataFrame,
    numeric_cols: list[str],
    derived_relationships: set,
) -> tuple[list, list]:
    """Calcule corrélations et filtre les relations dérivées.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        derived_relationships: Ensemble des relations dérivées détectées.

    Returns:
        Tuple (top_correlations, corr_pairs) pour réutilisation en aval.
    """
    corr_pairs = correlation_pvalues(df)

    if derived_relationships:
        corr_pairs = [
            p for p in corr_pairs
            if frozenset([p["column_a"], p["column_b"]]) not in derived_relationships
        ]

    top_correlations = _extract_top_correlations(corr_pairs)
    return top_correlations, corr_pairs


def _build_simulation_section(
    df: pd.DataFrame,
    typed_simulation: SimulationConfig,
) -> dict:
    """Exécute la simulation et retourne le dict résultat.

    Args:
        df: DataFrame pandas à analyser.
        typed_simulation: Configuration de simulation typée.

    Returns:
        Dictionnaire du résultat de simulation.
    """
    simulation = simulate_scenario(
        df,
        target=typed_simulation.target,
        feature=typed_simulation.feature,
        change_pct=typed_simulation.change_pct,
        baseline_feature_value=typed_simulation.baseline_feature_value,
        bounds=typed_simulation.bounds,
    )
    return simulation.to_dict()


def _extract_top_correlations(pairs: list, top_n: int = 5) -> list:
    """Extrait les N corrélations les plus fortes.

    Args:
        pairs: Liste des paires de corrélations.
        top_n: Nombre de corrélations à extraire.

    Returns:
        Liste des top_n corrélations triées par valeur absolue.
    """
    sorted_pairs = sorted(pairs, key=lambda p: abs(p["value"]), reverse=True)
    return sorted_pairs[:top_n]


def generate_report(
    df: pd.DataFrame,
    simulation_config: SimulationConfig | dict | None = None,
    analysis_config: AnalysisConfig | dict | None = None,
) -> ReportResult:
    """Génère le rapport d'analyse complet du DataFrame.

    Orchestre les sous-fonctions privées de construction de chaque section
    du rapport (anomalies, corrélations, simulation, saisonnalité, exploitabilité).

    Args:
        df: DataFrame source (issu de import_file).
        simulation_config: Configuration de simulation typée SimulationConfig
            ou dict équivalent.
        analysis_config: Configuration d'analyse typée AnalysisConfig
            ou dict équivalent.

    Returns:
        ReportResult typé contenant toutes les sections du rapport.
    """
    typed_simulation, typed_analysis = _normalize_configs(
        simulation_config, analysis_config
    )

    warnings: list[str] = []
    n_rows = len(df)

    if n_rows < SMALL_SAMPLE_THRESHOLD:
        warnings.append(
            f"Échantillon petit ({n_rows} lignes) : les résultats statistiques "
            f"(corrélations, détection d'anomalies, régression) sont indicatifs, "
            f"pas robustes. Recommandé : {SMALL_SAMPLE_THRESHOLD}+ lignes."
        )

    validation = validate_dataset(df)

    numeric_cols = legitimate_numeric_columns(df)
    profiling = {col: descriptive_stats(df[col]) for col in numeric_cols}

    if not numeric_cols:
        warnings.append(
            "Aucune colonne numérique exploitable détectée dans ce "
            "fichier : statistiques, corrélations, détection d'anomalies "
            "et simulation ne peuvent pas être calculées. Vérifiez que "
            "vos colonnes numériques sont bien reconnues comme telles "
            "(voir les limites de détection dans la documentation)."
        )

    # — Anomalies —
    anomalies = _build_anomalies_section(df, numeric_cols, typed_analysis.iqr_k)

    if anomalies:
        cols_with_anomalies = ", ".join(anomalies.keys())
        total_anomalies = sum(len(a["indices"]) for a in anomalies.values())
        warnings.append(
            f"Anomalie(s) détectée(s) sur {len(anomalies)} colonne(s) "
            f"({cols_with_anomalies}) : {total_anomalies} valeur(s) "
            f"hors de la plage habituelle au total, potentiellement des "
            f"erreurs de saisie ou des cas exceptionnels à vérifier - "
            f"elles peuvent fortement fausser la moyenne et l'écart-type "
            f"affichés."
        )

    # — Corrélations —
    derived_relationships = detect_derived_relationships(df, numeric_cols)
    top_correlations, corr_pairs = _build_correlations_section(df, numeric_cols, derived_relationships)
    _build_correlation_warnings(df, numeric_cols, corr_pairs, derived_relationships, warnings)
    
    # Détection des facteurs confondants pour les corrélations principales
    for corr in top_correlations[:3]:  # Vérifier les 3 premières corrélations
        confounders = detect_confounders(df, corr['column_a'], corr['column_b'])
        if confounders:
            warnings.append(
                f"Corrélation potentielle spurieuse entre {corr['column_a']} et {corr['column_b']} : "
                f"facteur(s) confondant(s) détecté(s) : {', '.join(confounders)}. "
                f"Cette corrélation pourrait être due à une variable tierce plutôt qu'à une relation directe."
            )
    
    # Détection des sous-groupes significatifs (seulement si des colonnes numériques existent)
    if numeric_cols:
        significant_subgroups = detect_significant_subgroups(df, numeric_cols[0])
        for subgroup in significant_subgroups:
            warnings.append(
                f"Sous-groupe significatif détecté : '{subgroup['column']}' explique "
                f"{subgroup['eta_squared']:.1%} de la variance de la cible. "
                f"Considérez une analyse segmentée par cette variable pour des insights plus précis."
            )

    # Détection de non-linéarité (P1.2)
    nonlinearity_patterns = _build_nonlinearity_warnings(df, numeric_cols, top_correlations, warnings)

    # — Simulation (optionnelle) —
    sim_dict: dict | None = None
    if typed_simulation is not None:
        sim_dict = _build_simulation_section(df, typed_simulation)
        _build_simulation_warnings(df, typed_simulation, sim_dict, n_rows, warnings, nonlinearity_patterns)

    # — R8 : Saisonnalité (avant R9 pour intégrer le warning au score) —
    _build_seasonality_warnings(df, corr_pairs, warnings)

    # — R9 : Score d'exploitabilité synthétique —
    sim_r_squared = (sim_dict or {}).get("model_r_squared")
    exploitability = _compute_exploitability_score(
        n_rows=n_rows,
        n_warnings=len(warnings),
        n_anomaly_cols=len(anomalies),
        r_squared=sim_r_squared,
    )

    return ReportResult(
        dataset_summary=DatasetSummary(
            n_rows=n_rows,
            n_columns=len(df.columns),
            numeric_columns=numeric_cols,
        ),
        validation=validation,
        profiling=profiling,
        anomalies=anomalies,
        top_correlations=top_correlations,
        warnings=warnings,
        exploitability=exploitability,
        simulation=sim_dict,
    )
