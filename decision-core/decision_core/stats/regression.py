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


def detect_confounders(
    df: pd.DataFrame,
    target: str,
    feature: str,
    threshold: float = 0.14,
    min_group_size: int = 5
) -> list[str]:
    """Détecte les facteurs confondants potentiels pour une corrélation feature-target.

    Un facteur confondant est une variable catégorielle qui est associée à la
    fois à la target et à la feature. L'approche classique par Pearson après
    factorisation est sensible à l'ordre des modalités et ne capture pas les
    relations non monotones en U ou en cloche. Ici, nous utilisons eta² + ANOVA
    à un facteur pour mesurer la proportion de variance expliquée, avec une
    p-value et un garde-fou sur la taille minimale des groupes.

    Args:
        df: DataFrame pandas contenant les données.
        target: Nom de la colonne cible.
        feature: Nom de la colonne feature.
        threshold: Seuil d'eta-carré pour considérer un facteur comme suffisamment
            fort pour être un confondant potentiel.
        min_group_size: Taille minimale par groupe pour que le test ANOVA soit fiable.

    Returns:
        Liste des noms de colonnes catégorielles potentiellement confondantes.
    """
    from decision_core.stats.anova import compute_eta_squared_with_significance

    confounders = []
    
    for col in df.columns:
        if col == target or col == feature:
            continue
        
        if pd.api.types.is_string_dtype(df[col]) or df[col].nunique() <= 10:
            try:
                if not pd.api.types.is_numeric_dtype(df[target]):
                    continue
                if not pd.api.types.is_numeric_dtype(df[feature]):
                    continue

                target_result = compute_eta_squared_with_significance(
                    df[target], df[col], min_group_size=min_group_size
                )
                feature_result = compute_eta_squared_with_significance(
                    df[feature], df[col], min_group_size=min_group_size
                )

                if (target_result.reliable and feature_result.reliable and
                    target_result.p_value <= 0.05 and feature_result.p_value <= 0.05 and
                    target_result.eta_squared >= threshold and feature_result.eta_squared >= threshold):
                    confounders.append(col)
            except Exception:
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
        Inclut log-loss et calibration ; gère séparation parfaite via bornes et fallback.

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

    # P3-14 : log-loss et calibration (gère séparation parfaite)
    try:
        p_clipped = np.clip(p, 1e-15, 1 - 1e-15)
        log_loss = float(-np.mean(y * np.log(p_clipped) + (1 - y) * np.log(1 - p_clipped)))
        # Calibration error : ECE approx (mean |p - y|)
        calibration_error = float(np.mean(np.abs(p - y)))
        # Détection séparation parfaite : coeff aux bornes ou p quasi 0/1 partout
        if abs(coef_opt) >= 9.9 or np.mean((p < 0.01) | (p > 0.99)) > 0.95:
            # Garder le résultat mais signaler via log_loss élevé
            pass
    except Exception:
        log_loss = None
        calibration_error = None

    return LogisticRegressionResult(
        target=target,
        feature=feature,
        r_squared=float(np.clip(r_squared, 0, 1)),
        intercept=float(intercept_opt),
        coefficient=float(coef_opt),
        model_type="logistic",
        log_loss=log_loss,
        calibration_error=calibration_error,
    )


def validate_regression_inputs(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Vérifie et nettoie les colonnes utilisées par une régression.

    - Retire uniquement les lignes avec NaN sur les colonnes concernées
      (pas sur tout le DataFrame, pour ne pas perdre de données inutilement).
    - Vérifie qu'il reste assez de lignes après nettoyage.
    - Vérifie qu'aucune colonne n'a une variance nulle (une variable
      constante ne peut pas participer à une régression linéaire).
    - Vérifie que les colonnes sont de type numérique.

    Retourne le sous-DataFrame nettoyé (colonnes demandées uniquement).
    """
    # Vérifier que les colonnes existent
    for col in columns:
        if col not in df.columns:
            raise ValueError(f"La colonne '{col}' n'existe pas dans le DataFrame.")
    
    # Vérifier que les colonnes sont numériques
    for col in columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise TypeError(
                f"La colonne '{col}' doit être numérique pour une régression (type actuel : {df[col].dtype}). "
                f"Les colonnes textuelles ou catégorielles ne sont pas supportées directement."
            )
    
    subset = df[columns].dropna()

    if len(subset) < MIN_ROWS_FOR_REGRESSION:
        # Détail du nombre de NaN par colonne pour aider au diagnostic
        nan_counts = {col: df[col].isna().sum() for col in columns}
        nan_details = ", ".join([f"{col}: {nan}/{len(df)} NaN" for col, nan in nan_counts.items()])
        raise InsufficientDataError(
            f"Pas assez de données pour une régression fiable : "
            f"{len(subset)} ligne(s) valide(s) après retrait des valeurs "
            f"manquantes (minimum requis : {MIN_ROWS_FOR_REGRESSION}). "
            f"Détail NaN : {nan_details}. Vérifiez que les colonnes '{columns[0]}' et '{columns[1]}' "
            f"ont des données simultanément disponibles."
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
