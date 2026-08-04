"""
Calculs d'analyse de variance (ANOVA) partagés pour decision-core.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class EtaSquaredResult:
    eta_squared: float
    p_value: float
    f_statistic: float
    n: int
    n_groups: int
    reliable: bool


def compute_eta_squared_with_significance(
    y: np.ndarray,
    groups: pd.Series,
    min_group_size: int = 5
) -> EtaSquaredResult:
    """Calcule l'eta-carré et sa significativité via un ANOVA à un facteur.

    Args:
        y: Tableau ou série de la variable cible numérique.
        groups: Série indiquant le groupe pour chaque observation.
        min_group_size: Taille minimale par groupe pour que le test soit fiable.

    Returns:
        EtaSquaredResult contenant eta_squared, p_value, f_statistic, n,
        n_groups et reliable.
    """
    df_temp = pd.DataFrame({'y': np.asarray(y), 'g': groups}).dropna()
    if df_temp.empty:
        return EtaSquaredResult(
            eta_squared=0.0,
            p_value=1.0,
            f_statistic=0.0,
            n=0,
            n_groups=0,
            reliable=False,
        )

    y_clean = df_temp['y'].values
    overall_mean = np.mean(y_clean)
    sst = np.sum((y_clean - overall_mean) ** 2)

    grouped = df_temp.groupby('g')['y']
    n_groups = grouped.ngroups
    n = len(df_temp)

    if n_groups < 2 or n <= n_groups:
        return EtaSquaredResult(
            eta_squared=0.0,
            p_value=1.0,
            f_statistic=0.0,
            n=n,
            n_groups=n_groups,
            reliable=False,
        )

    group_sizes = grouped.count().values
    if np.any(group_sizes < min_group_size):
        ssb = np.sum(group_sizes * (grouped.mean() - overall_mean) ** 2)
        eta_squared = float(ssb / sst) if sst > 0 else 0.0
        return EtaSquaredResult(
            eta_squared=eta_squared,
            p_value=1.0,
            f_statistic=0.0,
            n=n,
            n_groups=n_groups,
            reliable=False,
        )

    ssb = np.sum(group_sizes * (grouped.mean() - overall_mean) ** 2)
    ssw = np.sum(grouped.apply(lambda x: np.sum((x - np.mean(x)) ** 2)).values)

    eta_squared = float(ssb / sst) if sst > 0 else 0.0

    df_between = n_groups - 1
    df_within = n - n_groups

    msb = ssb / df_between if df_between > 0 else 0.0
    msw = ssw / df_within if df_within > 0 else 0.0

    if msw == 0:
        if ssb > 0:
            f_statistic = float('inf')
            p_value = 0.0
        else:
            f_statistic = 0.0
            p_value = 1.0
    else:
        f_statistic = float(msb / msw)
        p_value = float(stats.f.sf(f_statistic, df_between, df_within))

    return EtaSquaredResult(
        eta_squared=eta_squared,
        p_value=p_value,
        f_statistic=f_statistic,
        n=n,
        n_groups=n_groups,
        reliable=True,
    )


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
    return compute_eta_squared_with_significance(y, groups, min_group_size=1).eta_squared
