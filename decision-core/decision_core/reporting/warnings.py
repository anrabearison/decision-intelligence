"""
Détection de warnings contextuels pour decision-core.
"""
import re
import pandas as pd
from decision_core.profiling import MAX_COLUMNS_FOR_CORRELATION
from decision_core.anomaly_detection import MIN_RELIABLE_SAMPLE_SIZE
from decision_core.regression import validate_regression_inputs
from decision_core.influence_detection import detect_influential_points
from decision_core.derived_columns import detect_derived_relationships


SMALL_SAMPLE_THRESHOLD = MIN_RELIABLE_SAMPLE_SIZE
LOW_R_SQUARED_THRESHOLD = 0.3

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
) -> None:
    """Enrichit les warnings avec les informations sur la simulation.

    Args:
        df: DataFrame pandas à analyser.
        simulation_config: Configuration de la simulation.
        simulation_result: Résultat de la simulation.
        n_rows: Nombre de lignes du dataset.
        warnings: Liste des warnings à enrichir (modifiée en place).
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
