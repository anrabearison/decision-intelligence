"""
Module de régression - Phase 1a + 1b.

Choix assumé : régression linéaire par défaut (simple ou multivariée),
avec basculement automatique sur régression logistique pour les cibles binaires.

Robustesse (voir README, section limites) : les valeurs manquantes,
colonnes à variance nulle et échantillons trop petits sont détectés
explicitement avant tout calcul, via validate_regression_inputs -
jamais laissés fuiter en NaN silencieux ou en exception brute de scipy/numpy.

Phase 1b - Régression logistique : détection automatique des cibles binaires
et basculement sur régression logistique pour éviter les erreurs de modélisation
sur des événements binaires (Churn, Panne, Guéri, etc.).

Phase 1b - Encodage catégoriel : optionnellement encoder les variables catégorielles
en one-hot via le paramètre encode_categorical=True dans fit_simple_regression.
"""
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from decision_core.models import SimpleRegressionResult, MultivariateRegressionResult, LogisticRegressionResult

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


def is_binary_target(series: pd.Series) -> bool:
    """Détecte si une série est une cible binaire (exactement 2 valeurs uniques).

    Args:
        series: Série pandas à analyser.

    Returns:
        True si la série a exactement 2 valeurs uniques, False sinon.
    """
    unique_values = series.dropna().nunique()
    return unique_values == 2


def detect_confounders(df: pd.DataFrame, target: str, feature: str, threshold: float = 0.3) -> list[str]:
    """Détecte les facteurs confondants potentiels pour une corrélation feature-target.
    
    Un facteur confondant est une variable catégorielle qui est corrélée
    simultanément avec la feature et la target, suggérant que la corrélation
    observée pourrait être spurieuse.
    
    Args:
        df: DataFrame pandas contenant les données.
        target: Nom de la colonne cible.
        feature: Nom de la colonne feature.
        threshold: Seuil de corrélation pour considérer une variable comme confondant.
    
    Returns:
        Liste des noms de colonnes catégorielles potentiellement confondantes.
    """
    confounders = []
    
    # Parcourir toutes les colonnes catégorielles (texte)
    for col in df.columns:
        if col == target or col == feature:
            continue
        
        # Vérifier si la colonne est catégorielle (texte ou peu de valeurs uniques)
        if pd.api.types.is_string_dtype(df[col]) or df[col].nunique() <= 10:
            # Calculer la corrélation point-bisériale avec la target
            # Pour les variables catégorielles, on utilise la corrélation de Pearson
            # après encodage one-hot (première modalité)
            try:
                # Encodage simple : convertir en numérique via factorize
                encoded = pd.factorize(df[col])[0]
                # Ajouter explicitement l'index pour éviter la perte d'alignement
                encoded_series = pd.Series(encoded, index=df.index)
                
                if pd.api.types.is_numeric_dtype(df[target]):
                    corr_target = abs(df[target].corr(encoded_series))
                else:
                    corr_target = 0
                
                if pd.api.types.is_numeric_dtype(df[feature]):
                    corr_feature = abs(df[feature].corr(encoded_series))
                else:
                    corr_feature = 0
                
                # Si la variable est corrélée avec les deux, c'est un facteur confondant potentiel
                if corr_target >= threshold and corr_feature >= threshold:
                    confounders.append(col)
            except Exception:
                # Ignorer les erreurs de calcul de corrélation
                pass
    
    return confounders


def fit_logistic_regression(df: pd.DataFrame, target: str, feature: str) -> LogisticRegressionResult:
    """Ajuste une régression logistique pour une cible binaire.

    Args:
        df: DataFrame pandas contenant les données.
        target: Nom de la colonne cible (variable dépendante binaire).
        feature: Nom de la colonne feature (variable indépendante).

    Returns:
        LogisticRegressionResult contenant coefficient, intercept, r_squared, feature, target.

    Raises:
        TypeError: Si les colonnes ne sont pas numériques.
        InsufficientDataError: Si pas assez de données ou variance nulle.
    """
    if not pd.api.types.is_numeric_dtype(df[feature]):
        raise TypeError(f"La colonne '{feature}' doit être numérique pour une régression.")
    if not pd.api.types.is_numeric_dtype(df[target]):
        raise TypeError(f"La colonne '{target}' doit être numérique pour une régression.")

    clean = validate_regression_inputs(df, [feature, target])

    x = clean[feature].values
    y = clean[target].values

    # Régression logistique via maximum likelihood avec optimisation multivariée
    def negative_log_likelihood(params):
        """Fonction de coût pour la régression logistique."""
        intercept, coef = params
        # Éviter l'overflow dans exp
        z = intercept + coef * x
        z = np.clip(z, -500, 500)
        p = 1 / (1 + np.exp(-z))
        # Éviter log(0)
        p = np.clip(p, 1e-15, 1 - 1e-15)
        ll = y * np.log(p) + (1 - y) * np.log(1 - p)
        return -np.sum(ll)

    # Optimisation multivariée simultanée pour intercept et coefficient
    result = minimize(
        negative_log_likelihood,
        x0=[0.0, 0.0],  # Initialisation : intercept et coefficient
        method='L-BFGS-B',
        bounds=[(-10, 10), (-10, 10)]  # Bornes pour intercept et coefficient
    )
    
    intercept_opt, coef_opt = result.x

    # Calcul du pseudo-R² (McFadden)
    z = intercept_opt + coef_opt * x
    z = np.clip(z, -500, 500)
    p = 1 / (1 + np.exp(-z))
    
    # Log-vraisemblance du modèle
    ll_model = y * np.log(p) + (1 - y) * np.log(1 - p)
    ll_model = np.sum(ll_model)
    
    # Log-vraisemblance du modèle nul (intercept seulement)
    p_null = np.mean(y)
    ll_null = y * np.log(p_null) + (1 - y) * np.log(1 - p_null)
    ll_null = np.sum(ll_null)
    
    # Pseudo-R² de McFadden
    r_squared = 1 - (ll_model / ll_null)

    return LogisticRegressionResult(
        target=target,
        feature=feature,
        r_squared=float(r_squared),
        intercept=float(intercept_opt),
        coefficient=float(coef_opt),
        model_type="logistic",
    )


def validate_regression_inputs(df: pd.DataFrame, columns: list) -> pd.DataFrame:
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


def fit_simple_regression(
    df: pd.DataFrame, 
    target: str, 
    feature: str,
    encode_categorical: bool = False
) -> SimpleRegressionResult | LogisticRegressionResult:
    """Ajuste une régression simple entre deux variables.
    
    Détecte automatiquement si la cible est binaire et bascule sur régression logistique.
    Optionnellement encode les variables catégorielles en one-hot.

    Args:
        df: DataFrame pandas contenant les données.
        target: Nom de la colonne cible (variable dépendante).
        feature: Nom de la colonne feature (variable indépendante).
        encode_categorical: Si True, encode les variables catégorielles en one-hot.

    Returns:
        SimpleRegressionResult ou LogisticRegressionResult selon le type de cible.
        Utilisez .to_dict() pour obtenir un dictionnaire plat si nécessaire.

    Raises:
        TypeError: Si les colonnes ne sont pas numériques.
        InsufficientDataError: Si pas assez de données ou variance nulle.
    """
    from decision_core.stats.categorical import encode_categorical_features
    
    # Encodage optionnel des variables catégorielles
    if encode_categorical:
        df = encode_categorical_features(df)
    
    if not pd.api.types.is_numeric_dtype(df[feature]):
        raise TypeError(f"La colonne '{feature}' doit être numérique pour une régression.")
    if not pd.api.types.is_numeric_dtype(df[target]):
        raise TypeError(f"La colonne '{target}' doit être numérique pour une régression.")

    # Détection automatique de cible binaire
    if is_binary_target(df[target]):
        return fit_logistic_regression(df, target, feature)

    clean = validate_regression_inputs(df, [feature, target])

    x = clean[feature].values
    y = clean[target].values
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    return SimpleRegressionResult(
        target=target,
        feature=feature,
        r_squared=float(r_value ** 2),
        intercept=float(intercept),
        slope=float(slope),
    )


def fit_multivariate_regression(df: pd.DataFrame, target: str, features: list) -> MultivariateRegressionResult:
    """Ajuste une régression linéaire multivariée.

    Args:
        df: DataFrame pandas contenant les données.
        target: Nom de la colonne cible (variable dépendante).
        features: Liste des noms de colonnes features (variables indépendantes).

    Returns:
        MultivariateRegressionResult contenant intercept, coefficients, r_squared, target,
        condition_number, multicollinearity_warning.
        Utilisez .to_dict() pour obtenir un dictionnaire plat si nécessaire.

    Raises:
        TypeError: Si les colonnes ne sont pas numériques.
        InsufficientDataError: Si pas assez de données ou variance nulle.
    """
    for f in features + [target]:
        if not pd.api.types.is_numeric_dtype(df[f]):
            raise TypeError(f"La colonne '{f}' doit être numérique pour une régression.")

    clean = validate_regression_inputs(df, features + [target])

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

    X_standardized = (X - X.mean(axis=0)) / X.std(axis=0, ddof=1)
    X_standardized_with_intercept = np.column_stack([np.ones(len(X)), X_standardized])
    condition_number = float(np.linalg.cond(X_standardized_with_intercept))

    return MultivariateRegressionResult(
        target=target,
        r_squared=float(r_squared),
        intercept=intercept,
        coefficients=coefficients,
        condition_number=condition_number,
        multicollinearity_warning=condition_number > CONDITION_NUMBER_WARNING_THRESHOLD,
    )
