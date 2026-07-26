"""
Module de détection de type de colonne - Phase 1a.
Heuristique simple et documentée comme imparfaite (voir README).
"""
import pandas as pd


def detect_column_type(series: pd.Series) -> str:
    non_null = series.dropna()
    n = len(non_null)
    if n == 0:
        return "unknown"

    unique_count = non_null.nunique()

    # Booléen : exactement 2 valeurs distinctes ET reconnues comme booléennes
    # (pas n'importe quelle paire de catégories, ex: "Holstein"/"Jersey" reste catégoriel)
    BOOLEAN_PAIRS = [
        {"oui", "non"}, {"yes", "no"}, {"true", "false"}, {"vrai", "faux"},
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
