"""
Modèles de données typés (Configuration et Résultats) pour decision-core.
Encapsule les paramètres et résultats de simulation, régression, et
détection d'anomalies dans des Dataclasses pour assurer la clarté de l'API
et simplifier la maintenance.
"""
from dataclasses import dataclass, field, fields, asdict
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


# ---------------------------------------------------------------------------
# Modèles de rapport structuré
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DatasetSummary:
    """Résumé structuré du dataset analysé."""
    n_rows: int
    n_columns: int
    numeric_columns: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExploitabilityScore:
    """Score synthétique d'exploitabilité du dataset (R9).

    Attributes:
        level: Niveau qualitatif ('green', 'orange', 'red').
        score: Score numérique entre 0 et 100.
        summary: Texte explicatif à destination du décideur.
    """
    level: str
    score: int
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReportResult:
    """Résultat typé complet de generate_report.

    Encapsule toutes les sections du rapport d'analyse : résumé du dataset,
    validation, profiling, anomalies, corrélations, warnings, simulation
    optionnelle, et score d'exploitabilité.

    Supporte l'accès par clé dict (report["warnings"]) pour la
    rétrocompatibilité avec le code existant et les tests.
    """
    dataset_summary: DatasetSummary
    validation: dict[str, Any]
    profiling: dict[str, Any]
    anomalies: dict[str, Any]
    top_correlations: list[dict[str, Any]]
    warnings: list[str]
    exploitability: ExploitabilityScore
    simulation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Sérialise le rapport en dict brut pour JSON/FastAPI."""
        result: dict[str, Any] = {
            "dataset_summary": self.dataset_summary.to_dict(),
            "validation": self.validation,
            "profiling": self.profiling,
            "anomalies": self.anomalies,
            "top_correlations": self.top_correlations,
            "warnings": self.warnings,
            "exploitability": self.exploitability.to_dict(),
        }
        if self.simulation is not None:
            result["simulation"] = self.simulation
        return result

    # -- Rétrocompatibilité dict-like --
    # Permet report["warnings"], "simulation" in report, report.get("x", default)
    # pour ne pas casser le code existant (tests, renders, engine).
    # À terme, migrer vers l'accès par attribut (report.warnings).

    def __getitem__(self, key: str) -> Any:
        d = self.to_dict()
        return d[key]

    def __contains__(self, key: object) -> bool:
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        """Accès dict-like avec valeur par défaut."""
        d = self.to_dict()
        return d.get(key, default)

