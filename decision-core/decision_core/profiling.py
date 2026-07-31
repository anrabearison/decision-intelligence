"""
Module de profiling - Phase 1a.
"""
import itertools
import numpy as np
import pandas as pd
from scipy import stats
from decision_core.type_detection import is_identifier_column

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
    return {
        "mean": float(series.mean()),
        "std_dev": float(series.std()),
        "min": series.min().item() if hasattr(series.min(), "item") else series.min(),
        "max": series.max().item() if hasattr(series.max(), "item") else series.max(),
        "median": float(series.median()),
    }


def legitimate_numeric_columns(df: pd.DataFrame) -> list:
    """Colonnes numériques hors identifiants (ex: numéro de lot, ID
    séquentiel) - à utiliser partout où des statistiques ou corrélations
    sont calculées sur des colonnes numériques, pour rester cohérent
    (cf. correlation_matrix et generate_report, qui utilisaient chacun
    leur propre liste avant ce fix - trouvé en revue de code)."""
    numeric_df = df.select_dtypes(include="number")
    return [
        col for col in numeric_df.columns
        if not is_identifier_column(df[col])
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
