"""
Détection de warnings contextuels pour decision-core.
"""
import re
import numpy as np
import pandas as pd
from scipy import stats
from decision_core.stats.profiling import MAX_COLUMNS_FOR_CORRELATION
from decision_core.quality.anomaly_detection import MIN_RELIABLE_SAMPLE_SIZE
from decision_core.stats.regression import validate_regression_inputs
from decision_core.stats.influence_detection import detect_influential_points
from decision_core.stats.derived_columns import detect_derived_relationships
from decision_core.stats.nonlinearity import (
    QUADRATIC_P_VALUE_THRESHOLD,
    detect_quadratic_pattern,
    detect_step_pattern,
)
from decision_core.models.nonlinearity import StepPatternResult


SMALL_SAMPLE_THRESHOLD = MIN_RELIABLE_SAMPLE_SIZE
LOW_R_SQUARED_THRESHOLD = 0.3
ASYMMETRY_THRESHOLD = 0.4  # Calibré sur 18 domaines (21% des colonnes au-dessus)

# R8 — Détection de colonnes temporelles pour le warning de saisonnalité.
# Mots-clés cherchés dans les noms de colonnes (insensible à la casse).
_TEMPORAL_KEYWORDS = [
    "date", "semaine", "week", "mois", "month", "saison", "season",
    "trimestre", "quarter", "annee", "year", "jour", "day", "periode",
    "timestamp", "heure", "hour",
]


def _detect_temporal_columns(df: pd.DataFrame) -> list:
    """Retourne la liste des noms de colonnes dont le nom suggère une
    dimension temporelle (date, semaine, saison, etc.).

    La détection se fait par découpage du nom en mots (éparateurs _ - espace
    et split CamelCase) pour éviter les faux positifs sur des mots composés
    contenant un mot-clé temporel en sous-chaîne :
      - 'Bonjour' contient 'jour' mais n'est pas temporel → non détecté ✓
      - 'Budget_Par_Jour' → mots {'budget', 'par', 'jour'} → détecté ✓
      - 'DateVente' (CamelCase) → 'Date_Vente' → {'date', 'vente'} → détecté ✓

    Args:
        df: DataFrame pandas à analyser.

    Returns:
        Liste des noms de colonnes temporelles détectées.
    """
    found = []
    temporal_set = set(_TEMPORAL_KEYWORDS)
    for col in df.columns:
        # 1. Split CamelCase : 'DateVente' → 'Date_Vente'
        split_camel = re.sub(r'([a-z])([A-Z])', r'\1_\2', col)
        # 2. Normaliser les séparateurs et découper en mots
        parts = set(
            split_camel.lower()
            .replace("-", "_")
            .replace(" ", "_")
            .split("_")
        )
        # 3. Intersection avec les mots-clés temporels
        if parts & temporal_set:
            found.append(col)
    return found


def _build_seasonality_warnings(
    df: pd.DataFrame,
    corr_pairs: list,
    warnings: list[str],
) -> None:
    """R8 — Ajoute un warning si des colonnes temporelles + corrélations fortes
    sont détectées, signalant un risque de confusion saisonnière.

    Args:
        df: DataFrame pandas à analyser.
        corr_pairs: Liste des paires de corrélations.
        warnings: Liste des warnings à enrichir (modifiée en place).
    """
    temporal_cols = _detect_temporal_columns(df)
    if temporal_cols:
        strong_corrs = [
            p for p in corr_pairs
            if abs(p["value"]) >= 0.6 and p.get("significant_after_correction")
        ]
        if strong_corrs:
            temporal_names = ", ".join(f"'{c}'" for c in temporal_cols)
            warnings.append(
                f"Dimension temporelle détectée ({temporal_names}) : "
                f"les corrélations fortes observées peuvent refléter des "
                f"effets saisonniers plutôt que des relations causales "
                f"directes. Une hausse de prix en été (haute saison) "
                f"apparaît corrélée à la fréquentation, par exemple — "
                f"sans que le prix en soit la cause. Croiser avec une "
                f"analyse par période avant de tirer des conclusions."
            )


def _build_correlation_warnings(
    df: pd.DataFrame,
    numeric_cols: list[str],
    corr_pairs: list,
    derived_relationships: set,
    warnings: list[str],
) -> None:
    """Enrichit les warnings avec les informations sur les corrélations.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        corr_pairs: Liste des paires de corrélations.
        derived_relationships: Ensemble des relations dérivées détectées.
        warnings: Liste des warnings à enrichir (modifiée en place).
    """
    if derived_relationships:
        derived_names = sorted({name for pair in derived_relationships for name in pair})
        warnings.append(
            f"Relation calculée détectée entre {', '.join(derived_names)} : "
            f"une de ces colonnes semble dérivée mathématiquement des "
            f"autres (ex: Total = Prix × Quantité). Leur forte "
            f"corrélation n'est donc pas un insight - c'est une "
            f"conséquence directe du calcul, pas une découverte."
        )

    if len(numeric_cols) > MAX_COLUMNS_FOR_CORRELATION:
        warnings.append(
            f"Dataset large ({len(numeric_cols)} colonnes numériques) : "
            f"les corrélations ne sont calculées que sur les "
            f"{MAX_COLUMNS_FOR_CORRELATION} premières colonnes pour des "
            f"raisons de performance. Les statistiques descriptives "
            f"(moyenne, écart-type...) couvrent en revanche toutes les "
            f"colonnes."
        )

    n_tested = len(corr_pairs)
    n_significant = sum(1 for p in corr_pairs if p.get("significant_after_correction"))
    if n_tested >= 6 and n_significant < n_tested:
        warnings.append(
            f"Comparaisons multiples : sur {n_tested} paires de variables "
            f"testées, seulement {n_significant} restent statistiquement "
            f"significatives après correction (Benjamini-Hochberg, seuil "
            f"5%). Plus il y a de colonnes, plus une corrélation isolée "
            f"forte peut apparaître par hasard - se fier au champ "
            f"'significant_after_correction' de chaque paire plutôt qu'à "
            f"sa seule valeur."
        )


def _build_simulation_warnings(
    df: pd.DataFrame,
    simulation_config,
    simulation_result: dict,
    n_rows: int,
    warnings: list[str],
    nonlinearity_patterns: list = None,
) -> None:
    """Enrichit les warnings avec les informations sur la simulation.

    Args:
        df: DataFrame pandas à analyser.
        simulation_config: Configuration de la simulation.
        simulation_result: Résultat de la simulation.
        n_rows: Nombre de lignes du dataset.
        warnings: Liste des warnings à enrichir (modifiée en place).
        nonlinearity_patterns: Liste des patterns non-linéaires détectés (optionnel).
    """
    # Vérification de l'échantillon effectif (post-dropna sur les colonnes
    # utilisées) — un dataset de 40 lignes peut n'avoir que 5 valeurs
    # valides sur X et Y.
    effective_sample = validate_regression_inputs(
        df, [simulation_config.feature, simulation_config.target]
    )
    effective_n = len(effective_sample)
    if effective_n < n_rows and effective_n < SMALL_SAMPLE_THRESHOLD:
        warnings.append(
            f"Échantillon effectif réduit pour cette simulation : "
            f"seulement {effective_n} lignes valides sur "
            f"'{simulation_config.feature}' et "
            f"'{simulation_config.target}' (sur {n_rows} au total), "
            f"après retrait des valeurs manquantes - résultats "
            f"indicatifs, pas robustes."
        )

    if simulation_result["model_r_squared"] < LOW_R_SQUARED_THRESHOLD:
        warnings.append(
            f"R² faible ({simulation_result['model_r_squared']:.2f}) pour la "
            f"simulation sur '{simulation_config.feature}' : le modèle "
            f"explique moins de {int(LOW_R_SQUARED_THRESHOLD*100)}% de "
            f"la variance de '{simulation_config.target}' - la projection "
            f"est peu fiable, à interpréter avec beaucoup de prudence."
        )

    influence = detect_influential_points(
        df, feature=simulation_config.feature, target=simulation_config.target
    )
    if influence["indices"]:
        warnings.append(
            f"Point(s) influent(s) détecté(s) (ligne(s) "
            f"{influence['indices']}) : ce résultat dépend fortement "
            f"d'un ou plusieurs points spécifiques - une corrélation "
            f"ou une régression peut être largement déformée par un "
            f"seul point atypique. Vérifier ces valeurs avant de "
            f"s'y fier."
        )

    # Warning spécifique si la feature de simulation fait partie d'une relation non-linéaire
    if nonlinearity_patterns:
        for pattern in nonlinearity_patterns:
            if pattern.feature == simulation_config.feature:
                if isinstance(pattern, StepPatternResult):
                    warnings.append(
                        f"Relation non-linéaire détectée (paliers) entre "
                        f"'{pattern.feature}' et '{pattern.target}' : "
                        f"la simulation linéaire peut être trompeuse sur cette "
                        f"variable. La relation fonctionne par tranches de "
                        f"tarification ou seuils, pas par une droite continue."
                    )
                elif hasattr(pattern, "pattern_type"):
                    if pattern.pattern_type == "u_curve":
                        warnings.append(
                            f"Relation non-linéaire détectée (courbe en U) entre "
                            f"'{pattern.feature}' et '{pattern.target}' : "
                            f"la simulation linéaire peut être trompeuse sur cette "
                            f"variable. Les effets ne sont pas proportionnels - "
                            f"une augmentation de la feature peut avoir un impact "
                            f"différent selon le niveau de départ."
                        )
                    elif pattern.pattern_type == "optimum":
                        warnings.append(
                            f"Relation non-linéaire détectée (optimum) entre "
                            f"'{pattern.feature}' et '{pattern.target}' : "
                            f"la simulation linéaire peut être trompeuse sur cette "
                            f"variable. Il existe un niveau optimal de la feature "
                            f"au-delà duquel l'effet s'inverse - la simulation "
                            f"linéaire ne capture pas cette dynamique."
                        )


def _build_nonlinearity_warnings(
    df: pd.DataFrame,
    numeric_cols: list[str],
    top_correlations: list,
    warnings: list[str],
) -> list:
    """Détecte les patterns non-linéaires et ajoute des warnings pédagogiques.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        top_correlations: Liste des corrélations principales.
        warnings: Liste des warnings à enrichir (modifiée en place).

    Returns:
        Liste des patterns non-linéaires détectés (pour réutilisation dans _build_simulation_warnings).
    """
    nonlinearity_patterns = []

    # Limiter l'analyse aux paires de top_correlations pour éviter l'explosion combinatoire
    quadratic_results = []
    for corr in top_correlations:
        feature = corr["column_a"]
        target = corr["column_b"]

        quadratic_result = detect_quadratic_pattern(df, target, feature)
        if quadratic_result:
            quadratic_results.append(quadratic_result)

        # Détection de pattern par paliers
        step_result = detect_step_pattern(df, target, feature)
        if step_result:
            nonlinearity_patterns.append(step_result)
            warnings.append(
                f"Relation non-linéaire détectée (paliers) entre "
                f"'{step_result.feature}' et '{step_result.target}' : "
                f"la régression linéaire peut être trompeuse sur cette paire. "
                f"La relation fonctionne par tranches de tarification ou seuils, "
                f"pas par une droite continue."
            )

    if quadratic_results:
        raw_p_values = np.array([pattern.p_value for pattern in quadratic_results])
        adjusted_p_values = stats.false_discovery_control(raw_p_values, method="bh")

        for pattern, adjusted_p in zip(quadratic_results, adjusted_p_values):
            if adjusted_p > QUADRATIC_P_VALUE_THRESHOLD:
                continue

            nonlinearity_patterns.append(pattern)
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

    return nonlinearity_patterns


def _build_asymmetry_warnings(
    df: pd.DataFrame,
    numeric_cols: list[str],
    significant_subgroups: list,
    warnings: list[str],
    simulation_config=None,
    max_warnings: int = 3,
) -> None:
    """Détecte les distributions asymétriques et avertit sans changer la simulation.

    Le ratio |mean - median| / std > ASYMMETRY_THRESHOLD indique une asymétrie significative.
    Avec simulation, l'alerte est limitée à la cible et à la feature du scénario :
    ce sont les seules colonnes qui influencent directement la baseline présentée.
    Sans simulation, l'alerte reste descriptive et limitée aux colonnes les plus
    asymétriques pour éviter de transformer un signal utile en bruit.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        significant_subgroups: Liste des sous-groupes significatifs détectés (pour suggestion).
        warnings: Liste des warnings à enrichir (modifiée en place).
        simulation_config: Configuration de simulation optionnelle.
        max_warnings: Nombre maximum de warnings hors simulation.
    """
    if simulation_config is not None:
        relevant_cols = [
            col for col in [simulation_config.target, simulation_config.feature]
            if col in numeric_cols
        ]
        limit = len(relevant_cols)
    else:
        relevant_cols = list(numeric_cols)
        limit = max_warnings

    candidates = []
    for col in relevant_cols:
        mean_val = df[col].mean()
        median_val = df[col].median()
        std_val = df[col].std()

        if std_val > 0:
            asymmetry_ratio = abs(mean_val - median_val) / std_val

            if asymmetry_ratio > ASYMMETRY_THRESHOLD:
                candidates.append((asymmetry_ratio, col, mean_val, median_val))

    for asymmetry_ratio, col, mean_val, median_val in sorted(candidates, reverse=True)[:limit]:
        mean_str = f"{mean_val:,.2f}".replace(",", " ")
        median_str = f"{median_val:,.2f}".replace(",", " ")

        if simulation_config is not None and col == simulation_config.target:
            subject = f"Baseline de simulation peu représentative pour la cible '{col}'"
            interpretation = "La valeur de référence affichée peut ne pas représenter un cas typique."
        elif simulation_config is not None and col == simulation_config.feature:
            subject = f"Point de départ du scénario peu représentatif pour le levier '{col}'"
            interpretation = "Le changement simulé part d'une valeur moyenne qui peut ne pas représenter un cas typique."
        else:
            subject = f"Distribution asymétrique détectée pour '{col}'"
            interpretation = "Résultat à interpréter avec prudence."

        warning = (
            f"{subject} : la moyenne ({mean_str}) "
            f"est très éloignée de la médiane ({median_str}) à cause de valeurs "
            f"extrêmes (ratio asymétrie = {asymmetry_ratio:.2f}). "
            f"{interpretation}"
        )

        if significant_subgroups:
            subgroup = significant_subgroups[0]
            warning += f" Considérez une analyse segmentée par '{subgroup}'."

        warnings.append(warning)
