"""
Module de détection de points influents - Phase 1a.

Complète detect_anomalies_iqr (anomaly_detection.py) : IQR ne regarde
qu'une colonne à la fois et rate les points individuellement plausibles
mais incohérents avec la relation entre deux variables (vérifié
empiriquement - cf. tests). La distance de Cook mesure combien un point
retire de la droite de régression s'il est enlevé - c'est la métrique
appropriée pour ce cas, contrairement à IQR.

Utilisée pour avertir sur la fragilité d'une corrélation/régression,
jamais pour supprimer automatiquement un point (cohérent avec le
principe déjà appliqué ailleurs : signaler, ne jamais corriger à la
place de l'utilisateur).

Réutilise fit_simple_regression / validate_regression_inputs de
regression.py plutôt que d'appeler scipy directement : hérite ainsi
automatiquement des garde-fous NaN/variance nulle/échantillon
insuffisant (une duplication de cette logique avait initialement
réintroduit les mêmes bugs corrigés dans regression.py - cf. commit).
"""
import numpy as np
import pandas as pd
from decision_core.stats.regression import fit_simple_regression, validate_regression_inputs


# Seuil usuel en statistique appliquée pour signaler un point influent :
# D_i > 4/n (Cook, 1977 ; convention largement utilisée en pratique).
DEFAULT_THRESHOLD_RATIO = 4.0


def compute_cooks_distance(df: pd.DataFrame, feature: str, target: str) -> np.ndarray:
    """Calcule la distance de Cook pour chaque point d'une régression.

    Args:
        df: DataFrame pandas contenant les données.
        feature: Nom de la colonne feature (variable indépendante).
        target: Nom de la colonne cible (variable dépendante).

    Returns:
        Array numpy des distances de Cook pour chaque observation.
    """
    # Même nettoyage (dropna, vérification de variance) que la régression
    # utilisée pour le modèle - garantit la cohérence entre les deux.
    clean = validate_regression_inputs(df, [feature, target])
    model = fit_simple_regression(clean, target=target, feature=feature)

    # La distance de Cook est définie pour la régression linéaire OLS.
    # Si fit_simple_regression a basculé sur une régression logistique
    # (cible binaire), le concept de résidu OLS ne s'applique pas : on
    # retourne un tableau de zéros (= aucun point influent détecté).
    slope = getattr(model, "slope", None)
    if slope is None:
        x = clean[feature].values.astype(float)
        return np.zeros(len(x))

    x = clean[feature].values.astype(float)
    y = clean[target].values.astype(float)
    n = len(x)

    y_pred = model.intercept + slope * x
    residuals = y - y_pred


    p = 2  # nombre de paramètres estimés (pente + intercept)
    mse = np.sum(residuals ** 2) / (n - p)

    # Ajustement parfait (tous les résidus nuls) : le dénominateur de la
    # formule de Cook devient 0, produisant une division 0/0 sans ce
    # garde-fou. Convention : aucun point n'est "influent" quand le
    # modèle explique déjà tout parfaitement.
    if np.isclose(mse, 0.0):
        return np.zeros(n)

    x_mean = x.mean()
    ss_x = np.sum((x - x_mean) ** 2)
    leverage = 1 / n + (x - x_mean) ** 2 / ss_x

    cooks_d = (residuals ** 2 / (p * mse)) * (leverage / (1 - leverage) ** 2)
    return cooks_d



def detect_influential_points(
    df: pd.DataFrame, feature: str, target: str, threshold_ratio: float = DEFAULT_THRESHOLD_RATIO
) -> dict:
    """Détecte les points influents dans une régression linéaire.

    Args:
        df: DataFrame pandas contenant les données.
        feature: Nom de la colonne feature (variable indépendante).
        target: Nom de la colonne cible (variable dépendante).
        threshold_ratio: Ratio pour le seuil de Cook (défaut 4.0).

    Returns:
        Dictionnaire contenant indices, n, threshold, max_distance,
        max_distance_index.
    """
    cooks_d = compute_cooks_distance(df, feature, target)
    n = len(cooks_d)
    threshold = threshold_ratio / n

    # Les indices renvoyés sont ceux du DataFrame nettoyé (post-dropna),
    # pas nécessairement du df original si des lignes ont été retirées -
    # cohérent avec le comportement de validate_regression_inputs.
    clean = validate_regression_inputs(df, [feature, target])
    indices = clean.index[cooks_d > threshold].tolist()
    max_distance_index = int(clean.index[np.argmax(cooks_d)])


    return {
        "indices": indices,
        "n": n,
        "threshold": float(threshold),
        "max_distance": float(cooks_d.max()),
        "max_distance_index": max_distance_index,
    }
