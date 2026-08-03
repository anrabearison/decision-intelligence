"""
Modèles de données typés (Configuration et Résultats) pour decision-core.
Encapsule les paramètres et résultats de simulation, régression, et
détection d'anomalies dans des Dataclasses pour assurer la clarté de l'API
et simplifier la maintenance.
"""
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration typée pour le scénario de simulation."""
    target: str
    feature: str
    change_pct: float
    baseline_feature_value: float | None = None
    bounds: tuple[float, float] | None = None

    def __post_init__(self):
        """Valide la cohérence de la configuration."""
        if self.bounds is not None:
            min_val, max_val = self.bounds
            if min_val > max_val:
                raise ValueError(
                    f"bounds invalides : min_val ({min_val}) > max_val ({max_val}). "
                    f"La borne inférieure ne peut pas être supérieure à la borne supérieure."
                )


@dataclass(frozen=True)
class AnalysisConfig:
    """Configuration typée pour les paramètres d'analyse et de détection."""
    iqr_k: float = field(default=1.5)

    def __post_init__(self):
        if self.iqr_k <= 0:
            raise ValueError(f"iqr_k doit être strictement supérieur à 0 (valeur fournie : {self.iqr_k}).")


@dataclass(frozen=True)
class RegressionResult:
    """Encapsule les résultats d'une régression simple ou multivariée."""
    target: str
    r_squared: float
    intercept: float
    slope: float | None = None  # Présent uniquement en régression simple
    feature: str | None = None  # Présent uniquement en régression simple
    coefficients: dict[str, float] | None = None  # Présent uniquement en régression multivariée
    condition_number: float | None = None
    multicollinearity_warning: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convertit l'objet en dictionnaire brut pour compatibilité JSON/FastAPI."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True)
class SimulationResult:
    """Encapsule le résultat d'une simulation d'impact."""
    baseline: float
    simulated: float
    change_pct: float | None
    change_pct_reliable: bool
    model_r_squared: float
    feature: str
    target: str
    bounds_applied: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True)
class AnomalyDetectionResult:
    """Encapsule le résultat de la détection d'anomalies IQR."""
    indices: list[int]
    lower_bound: float
    upper_bound: float
    n: int
    reliable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
