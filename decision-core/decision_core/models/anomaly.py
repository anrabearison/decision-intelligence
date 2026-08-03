"""
Modèles de résultats de détection d'anomalies pour decision-core.
"""
from dataclasses import dataclass, asdict
from typing import Any


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
