"""
Module de détection d'anomalies - Phase 1a.
Méthode IQR. Limite documentée : peu fiable sous ~30 lignes (README) ;
le champ "reliable" du résultat le signale explicitement.
"""
import pandas as pd
from decision_core.models import AnomalyDetectionResult

MIN_RELIABLE_SAMPLE_SIZE = 30


def detect_anomalies_iqr(series: pd.Series, k: float = 1.5) -> AnomalyDetectionResult:
    """Détecte les anomalies dans une série numérique via la méthode IQR.

    Args:
        series: Série pandas numérique à analyser.
        k: Multiplicateur pour l'IQR (défaut 1.5, valeur usuelle de Tukey).

    Returns:
        AnomalyDetectionResult contenant les indices des anomalies,
        les bornes, et un indicateur de fiabilité.

    Raises:
        TypeError: Si la série n'est pas numérique.
        ValueError: Si k n'est pas strictement positif.
    """
    if k <= 0:
        raise ValueError(f"Le multiplicateur k doit être strictement positif (valeur fournie : {k}).")
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

    return AnomalyDetectionResult(
        indices=indices,
        lower_bound=float(lower_bound),
        upper_bound=float(upper_bound),
        n=n,
        reliable=n >= MIN_RELIABLE_SAMPLE_SIZE,
    )
