"""
Module de validation - Phase 1a.
Rôle : signaler les problèmes, jamais les corriger automatiquement
(limite volontaire, voir README).
"""
import pandas as pd


def validate_dataset(df: pd.DataFrame) -> dict:
    missing_values = {col: int(df[col].isna().sum()) for col in df.columns}

    # Les colonnes ressemblant à un identifiant (nom = "id") sont exclues de la
    # comparaison : deux lignes avec un id différent mais des données par
    # ailleurs identiques restent un doublon métier probable.
    comparison_cols = [c for c in df.columns if c.lower() != "id"]
    duplicates_count = int(df.duplicated(subset=comparison_cols).sum())

    return {
        "n_rows": len(df),
        "n_columns": len(df.columns),
        "duplicates_count": duplicates_count,
        "missing_values": missing_values,
    }
