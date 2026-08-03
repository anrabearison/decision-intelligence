"""
Modèles de configuration pour decision-core.
"""
from dataclasses import dataclass, field, fields
from typing import Any, Mapping


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

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "SimulationConfig":
        """Crée une instance à partir d'un mapping (ex: dict) en filtrant les clés inconnues."""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in mapping.items() if k in valid_keys}
        return cls(**filtered)


@dataclass(frozen=True)
class AnalysisConfig:
    """Configuration typée pour les paramètres d'analyse et de détection."""
    iqr_k: float = field(default=1.5)

    def __post_init__(self):
        if self.iqr_k <= 0:
            raise ValueError(f"iqr_k doit être strictement supérieur à 0 (valeur fournie : {self.iqr_k}).")

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "AnalysisConfig":
        """Crée une instance à partir d'un mapping (ex: dict) en filtrant les clés inconnues."""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in mapping.items() if k in valid_keys}
        return cls(**filtered)
