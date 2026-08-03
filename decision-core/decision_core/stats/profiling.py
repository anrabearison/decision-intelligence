"""
Module de profiling - Phase 1a.
"""
import itertools
import numpy as np
import pandas as pd
from scipy import stats
from decision_core.quality.type_detection import is_identifier_column

FDR_SIGNIFICANCE_LEVEL = 0.05

# Plafond de colonnes pour le calcul de corrélations : le nombre de
# paires croît en C(k,2), quadratique. Trouvé en audit de performance :
# 200 colonnes = 19900 paires = ~34s en synchrone, incompatible avec un
# traitement HTTP synchrone (timeouts usuels ~30s sur Railway/Render).
# Choix : plafonner plutôt que rejeter le fichier entier - le reste du
# rapport (profiling par colonne) reste peu coûteux et continue de
# couvrir toutes les colonnes, seul le calcul quadratique est limité.
MAX_COLUMNS_FOR_CORRELATION = 50


def descriptive_stats(series: pd.Series) -> dict:
    """Calcule les statistiques descriptives d'une série numérique.

    Args:
        series: Série pandas numérique.

    Returns:
        Dictionnaire contenant mean, std_dev, min, max, median.
    """
    return {
        "mean": float(series.mean()),
        "std_dev": float(series.std()),
        "min": series.min().item() if hasattr(series.min(), "item") else series.min(),
        "max": series.max().item() if hasattr(series.max(), "item") else series.max(),
        "median": float(series.median()),
    }


def legitimate_numeric_columns(df: pd.DataFrame) -> list:
    """Retourne les colonnes numériques légitimes (hors identifiants).

    Args:
        df: DataFrame pandas à analyser.

    Returns:
        Liste des noms de colonnes numériques qui ne sont pas des identifiants.
    """
    numeric_df = df.select_dtypes(include="number")
    return [
        col for col in numeric_df.columns
        if not is_identifier_column(df[col])
    ]


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Calcule la matrice de corrélation des colonnes numériques légitimes.

    Args:
        df: DataFrame pandas à analyser.

    Returns:
        DataFrame de corrélation (méthode de Pearson).
    """
    legitimate_cols = legitimate_numeric_columns(df)
    return df[legitimate_cols].corr()


def correlation_pvalues(df: pd.DataFrame) -> list:
    """Calcule les corrélations de Pearson avec p-values corrigées.

    Args:
        df: DataFrame pandas à analyser.

    Returns:
        Liste de dictionnaires contenant :
        - column_a, column_b: noms des colonnes
        - value: coefficient de corrélation
        - p_value: p-value brute
        - p_value_adjusted: p-value corrigée (Benjamini-Hochberg)
        - significant_after_correction: booléen indiquant la significativité

    Note:
        Utilise la correction Benjamini-Hochberg (FDR) plutôt que Bonferroni
        pour l'analyse exploratoire.
    """
    legitimate_cols = legitimate_numeric_columns(df)
    if len(legitimate_cols) > MAX_COLUMNS_FOR_CORRELATION:
        # Sélection déterministe (les N premières colonnes dans l'ordre
        # du fichier) plutôt qu'aléatoire - reproductible entre deux
        # analyses du même fichier.
        legitimate_cols = legitimate_cols[:MAX_COLUMNS_FOR_CORRELATION]

    pairs = []
    for col_a, col_b in itertools.combinations(legitimate_cols, 2):
        subset = df[[col_a, col_b]].dropna()
        if len(subset) < 3:
            continue
        r, p = stats.pearsonr(subset[col_a], subset[col_b])
        pairs.append({"column_a": col_a, "column_b": col_b, "value": float(r), "p_value": float(p)})

    if pairs:
        p_values = np.array([p["p_value"] for p in pairs])
        adjusted = stats.false_discovery_control(p_values, method="bh")
        for pair, adj_p in zip(pairs, adjusted):
            pair["p_value_adjusted"] = float(adj_p)
            pair["significant_after_correction"] = bool(adj_p < FDR_SIGNIFICANCE_LEVEL)

    return pairs
