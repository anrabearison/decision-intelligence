"""
Modèles de résultats de simulation pour decision-core.
"""
from dataclasses import dataclass, asdict
from typing import Any


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
    change_absolute: float | None = None
    change_percentage_points: float | None = None
    model_type: str | None = None
    bounds_applied: bool | None = None
    actionable: bool = True
    non_actionable_reason: str | None = None
    # P3 — Robustesse
    prediction_interval: dict[str, float] | None = None
    cross_validation: dict[str, float] | None = None
    warnings_structured: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}
