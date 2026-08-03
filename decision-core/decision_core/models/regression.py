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
class LogisticRegressionResult:
    """Encapsule les résultats d'une régression logistique pour cibles binaires."""
    target: str
    feature: str
    r_squared: float
    intercept: float
    coefficient: float  # coefficient de la feature (équivalent à slope)
    model_type: str = "logistic"  # pour distinguer de la régression linéaire

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
