"""
Modèles de rapport pour decision-core.
"""
from dataclasses import dataclass, asdict
from typing import Any


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


@dataclass(frozen=True)
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
    main_insight: str | None = None

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
        if self.main_insight is not None:
            result["main_insight"] = self.main_insight
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
