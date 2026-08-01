"""
Module de régression - Phase 1a.
Choix assumé : régression linéaire uniquement (simple ou multivariée),
sélection automatique fixe, pas de choix utilisateur de modèle
(voir README, section "Choix du modèle statistique").

Robustesse (voir README, section limites) : les valeurs manquantes,
colonnes à variance nulle et échantillons trop petits sont détectés
explicitement avant tout calcul, via _validate_regression_inputs -
jamais laissés fuiter en NaN silencieux ou en exception brute de scipy/numpy.
"""
import numpy as np
import pandas as pd
from scipy import stats

MIN_ROWS_FOR_REGRESSION = 3

# Seuils usuels du nombre de conditionnement pour détecter la
# multicolinéarité en régression (Belsley, Kuh & Welsch, 1980,
# "Regression Diagnostics") : préoccupation modérée au-delà de 30,
# sévère au-delà de 100. Choisi plutôt qu'un VIF par variable : sous-
# produit quasi gratuit de ce qui est déjà calculé, et capture la
# colinéarité agrégée entre 3+ variables, pas seulement paire à paire.
CONDITION_NUMBER_WARNING_THRESHOLD = 30


class InsufficientDataError(ValueError):
    """Levée quand une régression ne peut pas être calculée de façon fiable
    (trop peu de lignes après nettoyage des NaN, ou variance nulle sur une
    variable). Une régression sur si peu ou si peu variées de données
    produirait un résultat dégénéré (NaN ou division par zéro) plutôt
    qu'une exception claire - on préfère échouer explicitement."""
    pass


def _validate_regression_inputs(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Vérifie et nettoie les colonnes utilisées par une régression.

    - Retire uniquement les lignes avec NaN sur les colonnes concernées
      (pas sur tout le DataFrame, pour ne pas perdre de données inutilement).
    - Vérifie qu'il reste assez de lignes après nettoyage.
    - Vérifie qu'aucune colonne n'a une variance nulle (une variable
      constante ne peut pas participer à une régression linéaire).

    Retourne le sous-DataFrame nettoyé (colonnes demandées uniquement).
    """
    subset = df[columns].dropna()

    if len(subset) < MIN_ROWS_FOR_REGRESSION:
        raise InsufficientDataError(
            f"Pas assez de données pour une régression fiable : "
            f"{len(subset)} ligne(s) valide(s) après retrait des valeurs "
            f"manquantes (minimum requis : {MIN_ROWS_FOR_REGRESSION})."
        )

    for col in columns:
        if subset[col].std() == 0:
            raise InsufficientDataError(
                f"La colonne '{col}' a une variance nulle (valeur "
                f"constante) : une régression ne peut pas être calculée."
            )

    return subset


def fit_simple_regression(df: pd.DataFrame, target: str, feature: str) -> dict:
    if not pd.api.types.is_numeric_dtype(df[feature]):
        raise TypeError(f"La colonne '{feature}' doit être numérique pour une régression.")
    if not pd.api.types.is_numeric_dtype(df[target]):
        raise TypeError(f"La colonne '{target}' doit être numérique pour une régression.")

    clean = _validate_regression_inputs(df, [feature, target])

    x = clean[feature].values
    y = clean[target].values
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

    clean = _validate_regression_inputs(df, features + [target])

    X = clean[features].values
    X_with_intercept = np.column_stack([np.ones(len(X)), X])
    y = clean[target].values

    coefs, residuals, rank, sv = np.linalg.lstsq(X_with_intercept, y, rcond=None)
    intercept = float(coefs[0])
    coefficients = {features[i]: float(coefs[i + 1]) for i in range(len(features))}

    y_pred = X_with_intercept @ coefs
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r_squared = 1 - ss_res / ss_tot

    # Le nombre de conditionnement est sensible à l'échelle des variables,
    # pas seulement à leur colinéarité réelle - deux features indépendantes
    # mais d'échelles très différentes peuvent donner un conditionnement
    # élevé sans aucune vraie colinéarité (trouvé en écrivant les tests :
    # des features indépendantes donnaient ~1900, pas < 30 comme attendu).
    # Standardisation (centrage-réduction) avant calcul pour isoler la
    # vraie colinéarité des simples différences d'unités/échelles.
    # ddof=1 explicite : par cohérence avec pandas.std() (utilisé partout
    # ailleurs dans le codebase, ex: profiling.py, simulation.py), qui
    # calcule l'écart-type d'échantillon par défaut - contrairement à
    # numpy.std() qui utilise ddof=0 (population) par défaut. Sans impact
    # sur le résultat ici (le nombre de conditionnement est invariant à
    # une mise à l'échelle uniforme, vérifié empiriquement), mais évite
    # une incohérence de style qui pourrait dérouter un futur lecteur.
    X_standardized = (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)
    X_standardized_with_intercept = np.column_stack([np.ones(len(X)), X_standardized])
    condition_number = float(np.linalg.cond(X_standardized_with_intercept))

    return {
        "intercept": intercept,
        "coefficients": coefficients,
        "r_squared": float(r_squared),
        "target": target,
        "condition_number": condition_number,
        "multicollinearity_warning": condition_number > CONDITION_NUMBER_WARNING_THRESHOLD,
    }
