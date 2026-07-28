"""
Module de profiling - Phase 1a.
"""
import itertools
import numpy as np
import pandas as pd
from scipy import stats
from decision_core.type_detection import detect_column_type

FDR_SIGNIFICANCE_LEVEL = 0.05

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


def correlation_pvalues(df: pd.DataFrame) -> list:
    """Corrélations de Pearson avec p-value, corrigées pour comparaisons
    multiples (Benjamini-Hochberg / contrôle du taux de fausses
    découvertes). Choisi plutôt que Bonferroni : notre usage est
    exploratoire (repérer des pistes), pas confirmatoire - Bonferroni
    est trop conservateur et supprimerait quasiment tout signal dès
    10+ colonnes (croissance quadratique du nombre de paires testées).

    Trouvé en audit expert : sans correction, avec 15 colonnes
    indépendantes (aucune vraie relation) et n=30, la corrélation la
    plus forte dépassait 0.4 dans 97% des tirages, purement par hasard
    (problème classique des comparaisons multiples)."""
    legitimate_cols = legitimate_numeric_columns(df)
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
