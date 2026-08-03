"""
Modèles de résultats de régression pour decision-core.
"""
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class SimpleRegressionResult:
    """Encapsule les résultats d'une régression linéaire simple."""
    target: str
    feature: str
    r_squared: float
    intercept: float
    slope: float

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet en dictionnaire brut pour compatibilité JSON/FastAPI."""
        return asdict(self)


@dataclass(frozen=True)
class MultivariateRegressionResult:
    """Encapsule les résultats d'une régression linéaire multivariée."""
    target: str
    r_squared: float
    intercept: float
    coefficients: dict[str, float]
    condition_number: float
    multicollinearity_warning: bool

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet en dictionnaire brut pour compatibilité JSON/FastAPI."""
        return asdict(self)
