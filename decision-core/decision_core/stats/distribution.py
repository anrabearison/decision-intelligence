"""
Détection de distributions non-gaussiennes pour decision-core.

Ce module fournit trois détecteurs indépendants :
- données de comptage (count data)
- distribution zero-inflated
- queues lourdes / heavy tail

Les détecteurs produisent uniquement des warnings pédagogiques ; ils ne
modifient pas le modèle ni le flux de simulation.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True)
class CountDataDistributionResult:
    feature: str
    zero_ratio: float
    mean: float
    variance: float
    unique_values: int


@dataclass(frozen=True)
class ZeroInflatedDistributionResult:
    feature: str
    zero_ratio: float
    non_zero_mean: float
    unique_values: int


@dataclass(frozen=True)
class HeavyTailDistributionResult:
    feature: str
    skewness: float
    kurtosis: float
    tail_ratio: float
    positive_fraction: float


__all__ = [
    "CountDataDistributionResult",
    "ZeroInflatedDistributionResult",
    "HeavyTailDistributionResult",
    "detect_count_data_distribution",
    "detect_zero_inflation",
    "detect_heavy_tail",
]


def _is_integer_like(series: pd.Series, tol: float = 1e-8) -> bool:
    values = pd.to_numeric(series.dropna(), errors="coerce").to_numpy(dtype=float)
    return bool(values.size and np.all(np.abs(values - np.round(values)) <= tol))


def detect_count_data_distribution(
    series: pd.Series,
    min_rows: int = 10,
    max_unique_values: int = 12,
    max_value: float = 30.0,
    max_mean: float = 10.0,
) -> Optional[CountDataDistributionResult]:
    """Détecte une variable de comptage qui n'est pas adaptée à une loi normale."""
    values = pd.to_numeric(series.dropna(), errors="coerce")
    if len(values) < min_rows:
        return None

    if not _is_integer_like(values):
        return None

    if values.min() < 0:
        return None

    unique_values = int(values.nunique())
    if unique_values > max_unique_values or values.max() > max_value:
        return None

    mean = float(values.mean())
    if mean <= 0 or mean > max_mean:
        return None

    variance = float(values.var(ddof=1))
    zero_ratio = float((values == 0).sum()) / len(values)

    if unique_values <= 8 or zero_ratio >= 0.2:
        return CountDataDistributionResult(
            feature=series.name if series.name else "",
            zero_ratio=zero_ratio,
            mean=mean,
            variance=variance,
            unique_values=unique_values,
        )

    return None


def detect_zero_inflation(
    series: pd.Series,
    min_rows: int = 10,
    zero_threshold: float = 0.45,
) -> Optional[ZeroInflatedDistributionResult]:
    """Détecte une distribution zero-inflated non adaptée à un modèle gaussien."""
    values = pd.to_numeric(series.dropna(), errors="coerce")
    if len(values) < min_rows:
        return None

    unique_values = int(values.nunique())
    if unique_values <= 2:
        return None

    if values.min() < 0:
        return None

    zero_ratio = float((values == 0).sum()) / len(values)
    if zero_ratio <= zero_threshold:
        return None

    non_zero = values[values != 0]
    if len(non_zero) < 2:
        return None

    non_zero_mean = float(non_zero.mean())
    return ZeroInflatedDistributionResult(
        feature=series.name if series.name else "",
        zero_ratio=zero_ratio,
        non_zero_mean=non_zero_mean,
        unique_values=unique_values,
    )


def detect_heavy_tail(
    series: pd.Series,
    min_rows: int = 10,
    skew_threshold: float = 1.5,
    kurtosis_threshold: float = 1.0,
    tail_ratio_threshold: float = 5.0,
) -> Optional[HeavyTailDistributionResult]:
    """Détecte une distribution à queues lourdes qui viole l'hypothèse de normalité."""
    values = pd.to_numeric(series.dropna(), errors="coerce")
    if len(values) < min_rows:
        return None

    if values.min() < 0:
        return None

    if np.all(values == 0):
        return None

    skewness = float(stats.skew(values, nan_policy="omit"))
    kurtosis = float(stats.kurtosis(values, nan_policy="omit"))

    if skewness <= skew_threshold or kurtosis <= kurtosis_threshold:
        return None

    median = float(np.median(values))
    if median <= 0:
        return None

    p95 = float(np.percentile(values, 95))
    tail_ratio = p95 / median if median > 0 else 0.0
    if tail_ratio < tail_ratio_threshold:
        return None

    positive_fraction = float((values > 0).mean())
    return HeavyTailDistributionResult(
        feature=series.name if series.name else "",
        skewness=skewness,
        kurtosis=kurtosis,
        tail_ratio=tail_ratio,
        positive_fraction=positive_fraction,
    )
