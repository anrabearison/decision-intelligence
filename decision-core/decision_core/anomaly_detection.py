"""
Module de détection d'anomalies - Phase 1a.
Méthode IQR. Limite documentée : peu fiable sous ~30 lignes (README) ;
le champ "reliable" du résultat le signale explicitement.
"""
import pandas as pd

MIN_RELIABLE_SAMPLE_SIZE = 30


def detect_anomalies_iqr(series: pd.Series, k: float = 1.5) -> dict:
    if not pd.api.types.is_numeric_dtype(series):
        raise TypeError("La détection d'anomalies IQR requiert une série numérique.")

    n = len(series)
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - k * iqr
    upper_bound = q3 + k * iqr

    mask = (series < lower_bound) | (series > upper_bound)
    indices = series[mask].index.tolist()

    return {
        "indices": indices,
        "lower_bound": float(lower_bound),
        "upper_bound": float(upper_bound),
        "n": n,
        "reliable": n >= MIN_RELIABLE_SAMPLE_SIZE,
    }
