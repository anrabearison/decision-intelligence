"""
Module de validation - Phase 1a.
Rôle : signaler les problèmes, jamais les corriger automatiquement
(limite volontaire, voir README).
"""
import pandas as pd
from decision_core.quality.type_detection import is_identifier_column


def validate_dataset(df: pd.DataFrame) -> dict:
    """Valide un dataset et signale les problèmes.

    Args:
        df: DataFrame pandas à valider.

    Returns:
        Dictionnaire contenant :
        - n_rows: nombre de lignes
        - n_columns: nombre de colonnes
        - duplicates_count: nombre de doublons détectés
        - missing_values: dictionnaire {colonne: nombre de valeurs manquantes}
    """
    missing_values = {col: int(df[col].isna().sum()) for col in df.columns}

    # Les colonnes identifiant sont exclues de la comparaison de doublons :
    # deux lignes avec un identifiant différent mais des données par
    # ailleurs identiques restent un doublon métier probable. Détection
    # basée sur is_identifier_column (partagée avec profiling.py), pas
    # sur le nom de colonne "id" - une exclusion par nom exact ratait
    # tout identifiant nommé différemment ("Identifiant", "Numero",
    # "Code"...), très courant en français (trouvé en audit).
    comparison_cols = [c for c in df.columns if not is_identifier_column(df[c])]
    if not comparison_cols:
        # Cas limite trouvé en test : si TOUTES les colonnes ressemblent à
        # un identifiant (ex: deux colonnes de séquences 1..n), exclure
        # tout laisserait un subset vide - df.duplicated(subset=[]) plante
        # (erreur interne pandas). Repli : comparer sur toutes les
        # colonnes plutôt que de planter.
        comparison_cols = list(df.columns)
    duplicates_count = int(df.duplicated(subset=comparison_cols).sum())

    return {
        "n_rows": len(df),
        "n_columns": len(df.columns),
        "duplicates_count": duplicates_count,
        "missing_values": missing_values,
    }
