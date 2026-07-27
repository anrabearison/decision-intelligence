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
"""
import numpy as np
import pandas as pd
from scipy import stats

# Seuil usuel en statistique appliquée pour signaler un point influent :
# D_i > 4/n (Cook, 1977 ; convention largement utilisée en pratique).
DEFAULT_THRESHOLD_RATIO = 4.0


def compute_cooks_distance(df: pd.DataFrame, feature: str, target: str) -> np.ndarray:
    x = df[feature].values.astype(float)
    y = df[target].values.astype(float)
    n = len(x)

    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
    y_pred = intercept + slope * x
    residuals = y - y_pred

    p = 2  # nombre de paramètres estimés (pente + intercept)
    mse = np.sum(residuals ** 2) / (n - p)

    x_mean = x.mean()
    ss_x = np.sum((x - x_mean) ** 2)
    leverage = 1 / n + (x - x_mean) ** 2 / ss_x

    cooks_d = (residuals ** 2 / (p * mse)) * (leverage / (1 - leverage) ** 2)
    return cooks_d


def detect_influential_points(
    df: pd.DataFrame, feature: str, target: str, threshold_ratio: float = DEFAULT_THRESHOLD_RATIO
) -> dict:
    n = len(df)
    cooks_d = compute_cooks_distance(df, feature, target)
    threshold = threshold_ratio / n

    indices = df.index[cooks_d > threshold].tolist()
    max_distance_index = int(np.argmax(cooks_d))

    return {
        "indices": indices,
        "n": n,
        "threshold": float(threshold),
        "max_distance": float(cooks_d.max()),
        "max_distance_index": max_distance_index,
    }
