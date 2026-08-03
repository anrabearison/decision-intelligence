"""
Calculs d'analyse de variance (ANOVA) partagés pour decision-core.
"""
import numpy as np
import pandas as pd


def compute_eta_squared(y: np.ndarray, groups: pd.Series) -> float:
    """Calcule l'eta-carré (η²) entre une cible continue y et une variable de groupe.

    L'eta-carré mesure la proportion de variance de la cible expliquée par
    le groupe (SSB / SST).

    Args:
        y: Tableau ou série de la variable cible numérique.
        groups: Série indiquant le groupe pour chaque observation.

    Returns:
        Valeur de l'eta-carré entre 0.0 et 1.0.
    """
    y = np.asarray(y)
    overall_mean = np.mean(y)
    sst = np.sum((y - overall_mean) ** 2)

    if sst == 0:
        return 0.0

    df_temp = pd.DataFrame({'y': y, 'g': groups})
    grouped = df_temp.groupby('g')['y']

    ssb = np.sum(grouped.count() * (grouped.mean() - overall_mean) ** 2)
    return float(ssb / sst)
