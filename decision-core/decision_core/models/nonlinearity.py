"""
Modèles de résultats pour la détection de non-linéarité.
"""
from dataclasses import dataclass, asdict
from typing import Any, Literal


@dataclass(frozen=True)
class QuadraticPatternResult:
    """Résultat de la détection d'un pattern quadratique.

    Attributes:
        feature: Nom de la colonne feature.
        target: Nom de la colonne cible.
        pattern_type: Type de pattern ("u_curve" pour creux, "optimum" pour cloche).
        r2_linear_adj: R² ajusté du modèle linéaire.
        r2_quadratic_adj: R² ajusté du modèle quadratique.
        quadratic_coefficient: Coefficient quadratique c (y = a + bx + cx²).
        p_value: P-value du test de significativité du coefficient quadratique.
    """
    feature: str
    target: str
    pattern_type: Literal["u_curve", "optimum"]
    r2_linear_adj: float
    r2_quadratic_adj: float
    quadratic_coefficient: float
    p_value: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StepPatternResult:
    """Résultat de la détection d'un pattern par paliers.

    Attributes:
        feature: Nom de la colonne feature.
        target: Nom de la colonne cible.
        n_bins: Nombre de bins utilisés pour la discrétisation.
        r2_linear: R² du modèle linéaire simple.
        eta_squared_binned: Eta-carré du modèle par bins.
        p_value: P-value de l'ANOVA sur les bins.
        f_statistic: Statistique F de l'ANOVA sur les bins.
        bin_boundaries: Bornes des bins de discrétisation.
    """
    feature: str
    target: str
    n_bins: int
    r2_linear: float
    eta_squared_binned: float
    p_value: float
    f_statistic: float
    bin_boundaries: list[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
