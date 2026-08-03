"""
Module de détection de type de colonne - Phase 1a.
Heuristique simple et documentée comme imparfaite (voir README).
"""
import numpy as np
import pandas as pd


def detect_column_type(series: pd.Series) -> str:
    """Détecte le type d'une colonne pandas.

    Args:
        series: Série pandas à analyser.

    Returns:
        Une chaîne parmi : "numeric_continuous", "numeric_discrete",
        "categorical", "boolean", "datetime", "identifier", "text_free", "unknown".
    """
    non_null = series.dropna()
    n = len(non_null)
    if n == 0:
        return "unknown"

    unique_count = non_null.nunique()

    # Booléen : exactement 2 valeurs distinctes ET reconnues comme booléennes
    # (pas n'importe quelle paire de catégories, ex: "Holstein"/"Jersey" reste catégoriel)
    BOOLEAN_PAIRS = [
        {"oui", "non"}, {"yes", "no"}, {"true", "false"}, {"vrai", "faux"},
        {"o", "n"},  # abréviation française très courante (Oui/Non)
    ]
    if unique_count == 2 and not pd.api.types.is_numeric_dtype(series):
        values_lower = set(str(v).strip().lower() for v in non_null.unique())
        if values_lower in BOOLEAN_PAIRS:
            return "boolean"
    if unique_count == 2 and pd.api.types.is_numeric_dtype(series):
        if set(non_null.unique()) <= {0, 1}:
            return "boolean"

    # Numérique
    if pd.api.types.is_numeric_dtype(series):
        if (non_null.dropna() % 1 == 0).all():
            return "numeric_discrete"
        return "numeric_continuous"

    # Tentative de parsing de dates
    try:
        parsed = pd.to_datetime(non_null, errors="raise", format="mixed")
        if parsed.notna().all():
            return "datetime"
    except (ValueError, TypeError):
        pass

    # Identifiant : quasi toutes les valeurs sont uniques
    uniqueness_ratio = unique_count / n
    if uniqueness_ratio > 0.9 and n > 3:
        return "identifier"

    # Catégoriel : peu de valeurs uniques par rapport au nombre de lignes
    if uniqueness_ratio <= 0.5:
        return "categorical"

    return "text_free"


def _is_sequential_numeric_identifier(series: pd.Series) -> bool:
    """Détecte un identifiant numérique séquentiel (ex: 1, 2, 3, ...).

    detect_column_type() classe toute colonne numérique comme
    numeric_discrete/continuous avant même de vérifier si elle ressemble à
    un identifiant. Critère : pas constant de exactement ±1 entre valeurs
    consécutives - la signature d'un identifiant séquentiel (1,2,3... ou
    1001,1002,...), plus spécifique qu'une simple corrélation avec l'ordre
    des lignes (qui produirait un faux positif sur une vraie variable à
    tendance linéaire lisse, ex: une température augmentant de façon
    quasi parfaitement régulière - trouvé en audit)."""
    non_null = series.dropna()
    if len(non_null) < 4 or not pd.api.types.is_numeric_dtype(series):
        return False
    values = non_null.values
    if not np.all(values == np.floor(values)):
        return False
    diffs = np.diff(values)
    if len(diffs) == 0:
        return False
    return bool(np.all(diffs == diffs[0]) and abs(diffs[0]) == 1)


def is_identifier_column(series: pd.Series) -> bool:
    """Détecte si une colonne est un identifiant.

    Args:
        series: Série pandas à analyser.

    Returns:
        True si la colonne est un identifiant, False sinon.
    """
    return detect_column_type(series) == "identifier" or _is_sequential_numeric_identifier(series)
