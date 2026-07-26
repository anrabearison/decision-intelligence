"""
Module de régression - Phase 1a.
Choix assumé : régression linéaire uniquement (simple ou multivariée),
sélection automatique fixe, pas de choix utilisateur de modèle
(voir README, section "Choix du modèle statistique").
"""
import numpy as np
import pandas as pd
from scipy import stats


def fit_simple_regression(df: pd.DataFrame, target: str, feature: str) -> dict:
    if not pd.api.types.is_numeric_dtype(df[feature]):
        raise TypeError(f"La colonne '{feature}' doit être numérique pour une régression.")
    if not pd.api.types.is_numeric_dtype(df[target]):
        raise TypeError(f"La colonne '{target}' doit être numérique pour une régression.")

    x = df[feature].values
    y = df[target].values
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    return {
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(r_value ** 2),
        "feature": feature,
        "target": target,
    }


def fit_multivariate_regression(df: pd.DataFrame, target: str, features: list) -> dict:
    for f in features + [target]:
        if not pd.api.types.is_numeric_dtype(df[f]):
            raise TypeError(f"La colonne '{f}' doit être numérique pour une régression.")

    X = df[features].values
    X_with_intercept = np.column_stack([np.ones(len(X)), X])
    y = df[target].values

    coefs, residuals, rank, sv = np.linalg.lstsq(X_with_intercept, y, rcond=None)
    intercept = float(coefs[0])
    coefficients = {features[i]: float(coefs[i + 1]) for i in range(len(features))}

    y_pred = X_with_intercept @ coefs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot

    return {
        "intercept": intercept,
        "coefficients": coefficients,
        "r_squared": float(r_squared),
        "target": target,
    }
