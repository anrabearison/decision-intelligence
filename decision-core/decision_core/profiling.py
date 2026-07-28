"""
Module de profiling - Phase 1a.
"""
import numpy as np
import pandas as pd
from decision_core.type_detection import detect_column_type

# Seuil au-delà duquel une colonne numérique quasi-parfaitement corrélée à
# l'ordre des lignes est traitée comme un identifiant/index plutôt qu'une
# vraie variable explicative (ex: numéro de lot, ID séquentiel).
INDEX_LIKE_CORRELATION_THRESHOLD = 0.999


def descriptive_stats(series: pd.Series) -> dict:
    return {
        "mean": float(series.mean()),
        "std_dev": float(series.std()),
        "min": series.min().item() if hasattr(series.min(), "item") else series.min(),
        "max": series.max().item() if hasattr(series.max(), "item") else series.max(),
        "median": float(series.median()),
    }


def _is_index_like(series: pd.Series) -> bool:
    """Détecte un identifiant numérique séquentiel (ex: 1, 2, 3, ...).

    detect_column_type() classe toute colonne numérique comme
    numeric_discrete/continuous avant même de vérifier si elle ressemble à
    un identifiant (la branche 'identifier' de type_detection ne s'applique
    qu'aux colonnes non numériques). Un identifiant numérique comme
    'Numero_lot' passe donc entre les mailles - d'où cette vérification
    dédiée, basée sur la corrélation quasi parfaite avec l'ordre des lignes,
    plus fiable qu'un simple ratio d'unicité pour ce cas précis.
    """
    if len(series) < 4:
        return False
    row_order = np.arange(len(series))
    corr = np.corrcoef(series.values, row_order)[0, 1]
    return abs(corr) > INDEX_LIKE_CORRELATION_THRESHOLD


def legitimate_numeric_columns(df: pd.DataFrame) -> list:
    """Colonnes numériques hors identifiants (ex: numéro de lot, ID
    séquentiel) - à utiliser partout où des statistiques ou corrélations
    sont calculées sur des colonnes numériques, pour rester cohérent
    (cf. correlation_matrix et generate_report, qui utilisaient chacun
    leur propre liste avant ce fix - trouvé en revue de code)."""
    numeric_df = df.select_dtypes(include="number")
    return [
        col for col in numeric_df.columns
        if detect_column_type(df[col]) != "identifier" and not _is_index_like(df[col])
    ]


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    legitimate_cols = legitimate_numeric_columns(df)
    return df[legitimate_cols].corr()
