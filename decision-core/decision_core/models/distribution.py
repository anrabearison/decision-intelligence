"""Modèles de résultats pour la détection de distributions non-gaussiennes."""
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class CountDataDistributionResult:
    feature: str
    zero_ratio: float
    mean: float
    variance: float
    unique_values: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ZeroInflatedDistributionResult:
    feature: str
    zero_ratio: float
    non_zero_mean: float
    unique_values: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HeavyTailDistributionResult:
    feature: str
    skewness: float
    kurtosis: float
    tail_ratio: float
    positive_fraction: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
