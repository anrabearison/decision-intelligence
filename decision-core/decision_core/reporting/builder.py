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
    _build_asymmetry_warnings,
)
from decision_core.reporting.scoring import SMALL_SAMPLE_THRESHOLD
from decision_core.reporting.context import ReportBuildContext


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


def _initialize_context(
    df: pd.DataFrame,
    simulation_config: SimulationConfig | dict | None,
    analysis_config: AnalysisConfig | dict | None,
) -> ReportBuildContext:
    """Initialise le contexte de construction du rapport.

    Args:
        df: DataFrame source.
        simulation_config: Configuration de simulation typée ou dict.
        analysis_config: Configuration d'analyse typée ou dict.

    Returns:
        ReportBuildContext initialisé.
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
    
    return ReportBuildContext(
        df=df,
        typed_simulation=typed_simulation,
        typed_analysis=typed_analysis,
        warnings=warnings,
        n_rows=n_rows,
    )


def _populate_validation_and_profiling(ctx: ReportBuildContext) -> None:
    """Remplit la validation et le profiling dans le contexte.

    Args:
        ctx: Contexte de construction du rapport.
    """
    ctx.validation = validate_dataset(ctx.df)
    ctx.numeric_cols = legitimate_numeric_columns(ctx.df)
    ctx.profiling = {col: descriptive_stats(ctx.df[col]) for col in ctx.numeric_cols}
    
    if not ctx.numeric_cols:
        ctx.warnings.append(
            "Aucune colonne numérique exploitable détectée dans ce "
            "fichier : statistiques, corrélations, détection d'anomalies "
            "et simulation ne peuvent pas être calculées. Vérifiez que "
            "vos colonnes numériques sont bien reconnues comme telles "
            "(voir les limites de détection dans la documentation)."
        )


def _populate_anomalies(ctx: ReportBuildContext) -> None:
    """Remplit les anomalies dans le contexte.

    Args:
        ctx: Contexte de construction du rapport.
    """
    ctx.anomalies = _build_anomalies_section(
        ctx.df, ctx.numeric_cols, ctx.typed_analysis.iqr_k
    )
    
    if ctx.anomalies:
        cols_with_anomalies = ", ".join(ctx.anomalies.keys())
        total_anomalies = sum(len(a["indices"]) for a in ctx.anomalies.values())
        ctx.warnings.append(
            f"Anomalie(s) détectée(s) sur {len(ctx.anomalies)} colonne(s) "
            f"({cols_with_anomalies}) : {total_anomalies} valeur(s) "
            f"hors de la plage habituelle au total, potentiellement des "
            f"erreurs de saisie ou des cas exceptionnels à vérifier - "
            f"elles peuvent fortement fausser la moyenne et l'écart-type "
            f"affichés."
        )


def _populate_correlations(ctx: ReportBuildContext) -> None:
    """Remplit les corrélations et les warnings associés dans le contexte.

    Args:
        ctx: Contexte de construction du rapport.
    """
    ctx.derived_relationships = detect_derived_relationships(ctx.df, ctx.numeric_cols)
    ctx.top_correlations, ctx.corr_pairs = _build_correlations_section(
        ctx.df, ctx.numeric_cols, ctx.derived_relationships
    )
    _build_correlation_warnings(
        ctx.df, ctx.numeric_cols, ctx.corr_pairs, ctx.derived_relationships, ctx.warnings
    )
    
    # Détection des facteurs confondants pour les corrélations principales
    for corr in ctx.top_correlations[:3]:
        confounders = detect_confounders(ctx.df, corr['column_a'], corr['column_b'])
        if confounders:
            ctx.warnings.append(
                f"Corrélation potentielle spurieuse entre {corr['column_a']} et {corr['column_b']} : "
                f"facteur(s) confondant(s) détecté(s) : {', '.join(confounders)}. "
                f"Cette corrélation pourrait être due à une variable tierce plutôt qu'à une relation directe."
            )


def _populate_significant_subgroups(ctx: ReportBuildContext) -> None:
    """Remplit les sous-groupes significatifs dans le contexte.

    Args:
        ctx: Contexte de construction du rapport.
    """
    if not ctx.numeric_cols:
        return
    
    targets_to_scan = []
    if ctx.typed_simulation is not None and ctx.typed_simulation.target in ctx.numeric_cols:
        targets_to_scan = [ctx.typed_simulation.target]
    else:
        targets_to_scan = ctx.numeric_cols
    
    subgroup_map: dict[str, dict] = {}
    for target in targets_to_scan:
        for subgroup in detect_significant_subgroups(ctx.df, target):
            column = subgroup["column"]
            existing = subgroup_map.get(column)
            if existing is None or subgroup["eta_squared"] > existing["eta_squared"]:
                subgroup_map[column] = subgroup
    
    ctx.significant_subgroups = sorted(
        subgroup_map.values(),
        key=lambda s: s["eta_squared"],
        reverse=True,
    )[:5]
    
    for subgroup in ctx.significant_subgroups:
        ctx.warnings.append(
            f"Sous-groupe significatif détecté : '{subgroup['column']}' explique "
            f"{subgroup['eta_squared']:.1%} de la variance de la cible. "
            f"Considérez une analyse segmentée par cette variable pour des insights plus précis."
        )


def _populate_nonlinearity_and_asymmetry(ctx: ReportBuildContext) -> None:
    """Remplit les patterns non-linéaires et les warnings d'asymétrie.

    Args:
        ctx: Contexte de construction du rapport.
    """
    # Détection de non-linéarité (P1.2)
    ctx.nonlinearity_patterns, ctx.excluded_columns = _build_nonlinearity_warnings(
        ctx.df,
        ctx.numeric_cols,
        ctx.top_correlations,
        ctx.warnings,
        ctx.significant_subgroups,
        candidate_correlations=ctx.corr_pairs,
        simulation_config=ctx.typed_simulation,
    )
    
    # Détection d'asymétrie (F3)
    _build_asymmetry_warnings(
        ctx.df,
        ctx.numeric_cols,
        [s['column'] for s in ctx.significant_subgroups],
        ctx.warnings,
        simulation_config=ctx.typed_simulation,
        excluded_columns=list(ctx.excluded_columns),
    )


def _populate_simulation(ctx: ReportBuildContext) -> None:
    """Remplit la simulation si une configuration est fournie.

    Args:
        ctx: Contexte de construction du rapport.
    """
    if ctx.typed_simulation is not None:
        ctx.simulation = _build_simulation_section(ctx.df, ctx.typed_simulation)
        _build_simulation_warnings(
            ctx.df, ctx.typed_simulation, ctx.simulation, ctx.n_rows, ctx.warnings, ctx.nonlinearity_patterns
        )


def _populate_seasonality_and_score(ctx: ReportBuildContext) -> None:
    """Remplit la saisonnalité et calcule le score d'exploitabilité.

    Args:
        ctx: Contexte de construction du rapport.
    """
    # R8 : Saisonnalité (avant R9 pour intégrer le warning au score)
    _build_seasonality_warnings(ctx.df, ctx.corr_pairs, ctx.warnings)
    
    # R9 : Score d'exploitabilité synthétique
    sim_r_squared = (ctx.simulation or {}).get("model_r_squared")
    ctx.exploitability = _compute_exploitability_score(
        n_rows=ctx.n_rows,
        n_warnings=len(ctx.warnings),
        n_anomaly_cols=len(ctx.anomalies),
        r_squared=sim_r_squared,
    )


def _build_report_result(ctx: ReportBuildContext) -> ReportResult:
    """Construit le ReportResult final à partir du contexte.

    Args:
        ctx: Contexte de construction du rapport.

    Returns:
        ReportResult typé contenant toutes les sections du rapport.
    """
    return ReportResult(
        dataset_summary=DatasetSummary(
            n_rows=ctx.n_rows,
            n_columns=len(ctx.df.columns),
            numeric_columns=ctx.numeric_cols,
        ),
        validation=ctx.validation,
        profiling=ctx.profiling,
        anomalies=ctx.anomalies,
        top_correlations=ctx.top_correlations,
        warnings=ctx.warnings,
        exploitability=ctx.exploitability,
        simulation=ctx.simulation,
    )


def generate_report(
    df: pd.DataFrame,
    simulation_config: SimulationConfig | dict | None = None,
    analysis_config: AnalysisConfig | dict | None = None,
) -> ReportResult:
    """Génère le rapport d'analyse complet du DataFrame.

    Orchestre les étapes de construction du rapport via un contexte
    structuré pour améliorer la maintenabilité.

    Args:
        df: DataFrame source (issu de import_file).
        simulation_config: Configuration de simulation typée SimulationConfig
            ou dict équivalent.
        analysis_config: Configuration d'analyse typée AnalysisConfig
            ou dict équivalent.

    Returns:
        ReportResult typé contenant toutes les sections du rapport.
    """
    ctx = _initialize_context(df, simulation_config, analysis_config)
    _populate_validation_and_profiling(ctx)
    _populate_anomalies(ctx)
    _populate_correlations(ctx)
    _populate_significant_subgroups(ctx)
    _populate_nonlinearity_and_asymmetry(ctx)
    _populate_simulation(ctx)
    _populate_seasonality_and_score(ctx)
    return _build_report_result(ctx)
