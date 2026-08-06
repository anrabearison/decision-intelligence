"""
Warnings de non-linéarité P1.2 pour decision-core.
"""
import numpy as np
from scipy import stats
from decision_core.stats.nonlinearity import (
    QUADRATIC_P_VALUE_THRESHOLD,
    detect_quadratic_pattern,
    detect_step_pattern,
)
from decision_core.stats.regression import detect_confounders
from decision_core.models.nonlinearity import StepPatternResult
from .constants import MAX_NONLINEARITY_PAIRS, MAX_NONLINEARITY_WARNINGS

__all__ = ["_build_nonlinearity_warnings"]


def _build_nonlinearity_warnings(
    df: pd.DataFrame,
    numeric_cols: list[str],
    top_correlations: list,
    warnings: list[str],
    significant_subgroups: list[dict] | None = None,
    candidate_correlations: list[dict] | None = None,
    simulation_config=None,
    max_pairs: int = MAX_NONLINEARITY_PAIRS,
    max_warnings: int = MAX_NONLINEARITY_WARNINGS,
) -> tuple[list, set[str]]:
    """Détecte les patterns non-linéaires et ajoute des warnings pédagogiques.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        top_correlations: Liste des corrélations principales, conservée comme
            repli de compatibilité.
        warnings: Liste des warnings à enrichir (modifiée en place).
        candidate_correlations: Liste élargie de paires numériques à tester
            pour non-linéarité. Si absente, seules les top correlations sont
            utilisées (ancien comportement).
        simulation_config: Configuration de simulation optionnelle. Sa paire
            feature -> target est toujours ajoutée aux candidats si numérique.
        max_pairs: Plafond de paires non-linéaires testées.
        max_warnings: Nombre maximal de warnings P1.2 affichés dans le rapport.

    Returns:
        Tuple contenant les patterns non-linéaires détectés et les colonnes
        déjà couvertes par ces warnings.
    """
    # Import local pour éviter les dépendances circulaires
    from .distribution import _build_distribution_warnings
    
    nonlinearity_patterns = []
    significant_subgroups = significant_subgroups or []
    subgroup_eta_squared = {
        subgroup["column"]: subgroup["eta_squared"]
        for subgroup in significant_subgroups
    }

    def _has_strong_confounder(feature: str, target: str) -> bool:
        confounders = detect_confounders(df, target, feature)
        return any(subgroup_eta_squared.get(confounder, 0) > 0.5 for confounder in confounders)

    def _candidate_pairs() -> list[tuple[str, str]]:
        source = candidate_correlations if candidate_correlations is not None else top_correlations
        pairs: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()

        def add_pair(feature: str, target: str) -> None:
            if feature == target:
                return
            if feature not in numeric_cols or target not in numeric_cols:
                return
            key = (feature, target)
            if key in seen:
                return
            seen.add(key)
            pairs.append(key)

        if simulation_config is not None:
            add_pair(simulation_config.feature, simulation_config.target)

        for corr in source:
            add_pair(corr["column_a"], corr["column_b"])
            if len(pairs) >= max_pairs:
                break

        return pairs

    def _explanatory_gain(pattern) -> float:
        if isinstance(pattern, StepPatternResult):
            return pattern.eta_squared_binned - pattern.r2_linear
        return pattern.r2_quadratic_adj - pattern.r2_linear_adj

    # Scanner les paires candidates élargies : toutes les corrélations calculées
    # sur les jeux raisonnables, plafonnées sur les datasets larges.
    quadratic_results = []
    step_results = []
    for feature, target in _candidate_pairs():
        if _has_strong_confounder(feature, target):
            continue

        quadratic_result = detect_quadratic_pattern(df, target, feature)
        if quadratic_result:
            quadratic_results.append(quadratic_result)

        # Détection de pattern par paliers
        step_result = detect_step_pattern(df, target, feature)
        if step_result:
            step_results.append(step_result)

    display_candidates = []
    quadratic_validated_pairs = set()
    if quadratic_results:
        raw_p_values = np.array([pattern.p_value for pattern in quadratic_results])
        adjusted_p_values = stats.false_discovery_control(raw_p_values, method="bh")

        for pattern, adjusted_p in zip(quadratic_results, adjusted_p_values):
            if adjusted_p > QUADRATIC_P_VALUE_THRESHOLD:
                continue

            quadratic_validated_pairs.add((pattern.feature, pattern.target))
            nonlinearity_patterns.append(pattern)
            display_candidates.append((pattern, adjusted_p))

    for step_result in step_results:
        if (step_result.feature, step_result.target) in quadratic_validated_pairs:
            continue

        nonlinearity_patterns.append(step_result)
        display_candidates.append((step_result, None))

    display_candidates.sort(
        key=lambda item: (
            _explanatory_gain(item[0]),
            -item[0].p_value,
        ),
        reverse=True,
    )

    for pattern, adjusted_p in display_candidates[:max_warnings]:
        if isinstance(pattern, StepPatternResult):
            warnings.append(
                f"Relation non-linéaire détectée (paliers) entre "
                f"'{pattern.feature}' et '{pattern.target}' : "
                f"la régression linéaire peut être trompeuse sur cette paire. "
                f"La relation fonctionne par tranches de tarification ou seuils, "
                f"pas par une droite continue."
            )
            continue

        p_validation = (
            f"p ajustée = {adjusted_p:.2f}"
            f" (p brute = {pattern.p_value:.2f})"
        )
        if pattern.p_value <= 0.05:
            discovery_type = "Relation non-linéaire détectée"
        else:
            discovery_type = "Relation non-linéaire potentielle détectée"

        if pattern.pattern_type == "u_curve":
            warnings.append(
                f"{discovery_type} (courbe en U) entre "
                f"'{pattern.feature}' et '{pattern.target}' : "
                f"la régression linéaire peut être trompeuse sur cette paire. "
                f"Les effets ne sont pas proportionnels - une augmentation de "
                f"la feature peut avoir un impact différent selon le niveau de départ. "
                f"Signal validé après correction Benjamini-Hochberg ({p_validation})."
            )
        elif pattern.pattern_type == "optimum":
            warnings.append(
                f"{discovery_type} (optimum) entre "
                f"'{pattern.feature}' et '{pattern.target}' : "
                f"la régression linéaire peut être trompeuse sur cette paire. "
                f"Il existe un niveau optimal de la feature au-delà duquel "
                f"l'effet s'inverse - la simulation linéaire ne capture pas "
                f"cette dynamique. Signal validé après correction "
                f"Benjamini-Hochberg ({p_validation})."
            )

    covered_columns = _build_distribution_warnings(df, numeric_cols, warnings)
    return nonlinearity_patterns, covered_columns
