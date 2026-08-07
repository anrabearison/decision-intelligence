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
from decision_core.reporting.warnings.seasonality import _detect_temporal_columns
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
        # P1-7 : IQR contextualisé — si sous-groupe fort explique la colonne, dire segment métier
        cols_with_anomalies = list(ctx.anomalies.keys())
        cols_str = ", ".join(cols_with_anomalies)
        total_anomalies = sum(len(a["indices"]) for a in ctx.anomalies.values())
        # Vérifier si un sous-groupe fort existe déjà (sinon on le fera après, mais on tente)
        subgroup_cols = []
        try:
            subgroup_cols = [s["column"] for s in ctx.significant_subgroups]
        except Exception:
            pass
        if subgroup_cols:
            top_sub = subgroup_cols[0]
            ctx.warnings.append(
                f"Anomalie(s) détectée(s) sur {len(ctx.anomalies)} colonne(s) "
                f"({cols_str}) : {total_anomalies} valeur(s) "
                f"hors de la plage habituelle. Valeurs atypiques — elles peuvent être des erreurs, "
                f"ou représenter un segment métier à analyser séparément. "
                f"Ces valeurs atypiques semblent liées à '{top_sub}' : segment métier probable."
            )
        else:
            ctx.warnings.append(
                f"Anomalie(s) détectée(s) sur {len(ctx.anomalies)} colonne(s) "
                f"({cols_str}) : {total_anomalies} valeur(s) "
                f"hors de la plage habituelle. Valeurs atypiques — elles peuvent être des erreurs de saisie, "
                f"ou représenter un segment métier distinct — vérifiez avant de les corriger."
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
    
    # P1-8 : saisonnalité mieux nommée — si colonne temporelle, dire effet saisonnier
    temporal_cols = set(_detect_temporal_columns(ctx.df))

    for subgroup in ctx.significant_subgroups:
        col = subgroup["column"]
        eta = subgroup["eta_squared"]
        if col in temporal_cols:
            ctx.warnings.append(
                f"Effet saisonnier/temporel fort détecté : '{col}' explique {eta:.0%} des écarts "
                f"— bien plus qu'une simple segmentation. Comparer des périodes sans tenir compte de la saison "
                f"peut fausser l'analyse. Analysez par période avant de conclure."
            )
        else:
            ctx.warnings.append(
                f"Sous-groupe significatif détecté : '{col}' explique "
                f"{eta:.1%} de la variance de la cible (explique {eta:.0%} des écarts). "
                f"Considérez une analyse segmentée par cette variable pour des insights plus précis."
            )

    # P1-7 (suite) : si anomalies existent et sous-groupe fort, contextualiser
    if ctx.anomalies and ctx.significant_subgroups:
        # On ne répète pas si le warning anomalies contenait déjà le sous-groupe
        already_contextualized = any("segment métier" in w for w in ctx.warnings)
        if not already_contextualized:
            top = ctx.significant_subgroups[0]["column"]
            cols = ", ".join(ctx.anomalies.keys())
            ctx.warnings.append(
                f"Ces valeurs atypiques ({cols}) semblent liées à '{top}' : "
                f"segment métier probable — analysez séparément plutôt que comme erreurs."
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
        # P0-2 : bandeau simulation non exploitable si actionable=False
        if ctx.simulation.get("actionable") is False:
            ctx.warnings.append(
                f"Simulation non exploitable : {ctx.simulation.get('non_actionable_reason','Raison non spécifiée')} "
                f"Calcul indicatif uniquement — ne pas utiliser pour une décision."
            )
        _build_simulation_warnings(
            ctx.df, ctx.typed_simulation, ctx.simulation, ctx.n_rows, ctx.warnings, ctx.nonlinearity_patterns
        )
        # P0-4 : warning spécifique paliers métier même si R² n'est pas quasi nul
        if ctx.simulation.get("actionable") is False and "paliers" in (ctx.simulation.get("non_actionable_reason") or ""):
            # Déjà couvert par le bandeau, mais on ajoute un warning métier explicite si pas déjà présent
            paliers_msg = (
                f"La variable '{ctx.typed_simulation.feature}' semble fonctionner par paliers/seuils métier. "
                f"Une simulation continue en pourcentage est trompeuse — préférez une simulation par passage de tranche."
            )
            if paliers_msg not in ctx.warnings:
                ctx.warnings.append(paliers_msg)


def _populate_seasonality_and_score(ctx: ReportBuildContext) -> None:
    """Remplit la saisonnalité et calcule le score d'exploitabilité.

    Args:
        ctx: Contexte de construction du rapport.
    """
    # R8 : Saisonnalité (avant R9 pour intégrer le warning au score)
    _build_seasonality_warnings(ctx.df, ctx.corr_pairs, ctx.warnings)

    # P2-9 : Churn par segment — si cible binaire + colonnes catégorielles
    try:
        from decision_core.stats.regression import is_binary_target
        from decision_core.stats.categorical import detect_significant_subgroups as _detect_sub

        # Déterminer la cible (simulation ou première numérique binaire)
        target_col = None
        if ctx.typed_simulation is not None:
            target_col = ctx.typed_simulation.target
        else:
            for col in ctx.df.columns:
                try:
                    if is_binary_target(ctx.df[col]):
                        target_col = col
                        break
                except Exception:
                    continue
        if target_col is not None and target_col in ctx.df.columns and is_binary_target(ctx.df[target_col]):
            cat_cols = [c for c in ctx.df.columns if c != target_col and ctx.df[c].dtype == object or str(ctx.df[c].dtype) == 'object' or pd.api.types.is_string_dtype(ctx.df[c])]
            # limiter à 2 colonnes max pour éviter le spam
            for cat in cat_cols[:2]:
                if ctx.df[cat].nunique() <= 10 and ctx.df[cat].nunique() > 1:
                    rates = ctx.df.groupby(cat)[target_col].mean().sort_values(ascending=False)
                    if len(rates) >= 2:
                        parts = ", ".join(f"{idx}: {val:.0%}" for idx, val in rates.items())
                        ctx.warnings.append(
                            f"Taux de '{target_col}' par segment '{cat}' : {parts}. "
                            f"Cette segmentation peut révéler les segments à risque plus que la moyenne globale."
                        )
    except Exception:
        pass

    # P2-10 : Plafonds physiques — si simulation dépasse borne plausible
    try:
        sim = ctx.simulation or {}
        if sim and sim.get("target"):
            target = sim["target"]
            simulated = sim.get("simulated")
            # Détection heuristique : Note sur 20, pourcentage 0-100, proba 0-1
            bounds = None
            low_target = target.lower()
            if "note" in low_target and "20" in low_target:
                bounds = (0, 20)
            elif "pourcent" in low_target or "pct" in low_target or "taux" in low_target:
                bounds = (0, 100)
            elif "proba" in low_target or target.lower() == "churn":
                bounds = (0, 1)
            if bounds and simulated is not None:
                if not (bounds[0] <= simulated <= bounds[1]):
                    ctx.warnings.append(
                        f"Simulation hors borne plausible pour '{target}' : {simulated:.2f} "
                        f"hors [{bounds[0]}, {bounds[1]}]. Le modèle linéaire dépasse une limite physique — "
                        f"interprétez comme indicatif, pas comme valeur réalisable."
                    )
    except Exception:
        pass
    
    # R9 : Score d'exploitabilité synthétique
    sim_r_squared = (ctx.simulation or {}).get("model_r_squared")
    ctx.exploitability = _compute_exploitability_score(
        n_rows=ctx.n_rows,
        n_warnings=len(ctx.warnings),
        n_anomaly_cols=len(ctx.anomalies),
        r_squared=sim_r_squared,
    )


def _build_main_insight(ctx: ReportBuildContext) -> str | None:
    """P1-5 : génère une phrase priorisée en tête de rapport.

    Priorités déterministes :
    1. simulation non exploitable
    2. simulation par paliers
    3. confounder fort
    4. sous-groupe dominant
    5. non-linéarité
    6. asymétrie/distribution
    7. saisonnalité
    8. meilleure corrélation fiable
    """
    sim = ctx.simulation or {}
    # 1. simulation non exploitable (R² quasi nul)
    if sim.get("actionable") is False and sim.get("non_actionable_reason"):
        reason = sim["non_actionable_reason"]
        if "R²" in reason or "n'explique" in reason:
            return (
                f"Votre simulation globale n'est pas fiable : {reason} "
                f"Envisagez une analyse segmentée avant de décider."
            )
        if "paliers" in reason:
            return (
                f"La variable '{sim.get('feature','?')}' semble fonctionner par paliers. "
                f"Une simulation continue est trompeuse — préférez une analyse par tranche."
            )

    # 2. confounder fort (déjà dans warnings)
    for w in ctx.warnings:
        if "facteur(s) confondant(s)" in w or "spurieuse" in w:
            # extraire les noms si possible
            return w + " Vérifiez ce facteur avant d'interpréter la corrélation comme causale."

    # 3. sous-groupe dominant
    if ctx.significant_subgroups:
        top = ctx.significant_subgroups[0]
        eta = top.get("eta_squared", 0)
        if eta >= 0.5:
            sim_feat = (ctx.typed_simulation.feature if ctx.typed_simulation else None)
            return (
                f"La variable '{top['column']}' explique {eta:.0%} des écarts — bien plus que votre feature "
                f"'{sim_feat or 'testée'}'. Analysez séparément par '{top['column']}' avant de simuler globalement."
            )

    # 4. non-linéarité
    if ctx.nonlinearity_patterns:
        p = ctx.nonlinearity_patterns[0]
        return (
            f"Relation non-linéaire détectée entre '{p.feature}' et '{p.target}' : "
            f"la droite ne capture pas l'effet réel — la simulation linéaire est à interpréter avec prudence."
        )

    # 5. asymétrie/distribution — premier warning significatif
    for w in ctx.warnings:
        if "asymétrique" in w.lower() or "queue lourde" in w.lower() or "beaucoup de valeurs à zéro" in w.lower():
            return w

    # 6. saisonnalité
    for w in ctx.warnings:
        if "saisonnier" in w.lower() or "temporelle" in w.lower():
            return w

    # 7. meilleure corrélation fiable
    for c in ctx.top_correlations:
        if c.get("significant_after_correction"):
            return (
                f"Signal le plus fiable : '{c['column_a']}' ↔ '{c['column_b']}' "
                f"(r={c['value']:.2f}, significatif après correction)."
            )

    if ctx.warnings:
        return ctx.warnings[0]
    return None


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
        main_insight=ctx.main_insight,
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
    ctx.main_insight = _build_main_insight(ctx)
    return _build_report_result(ctx)
