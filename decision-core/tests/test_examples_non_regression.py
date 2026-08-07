"""
Non-régression sur les 18 CSV d'examples — seuils P1.2 gelés.

Objectif : protéger les calibrages documentés dans CHANGELOG.md et
docs/RAPPORT_TESTS_DOMAINES.md contre une dérive silencieuse :
- seuils quadratiques (QUADRATIC_IMPROVEMENT=0.04, QUADRATIC_P_VALUE=0.10)
- seuils paliers (ETA_SQUARED_IMPROVEMENT=0.02)
- plafonds MAX_NONLINEARITY_PAIRS/WARNINGS

Ce fichier est branché à pytest (pyproject.toml testpaths = ["tests"])
et remplace l'ancien test_all_examples.py (script manuel non exécuté en CI).
Chaque exemple doit rester importable et produire un rapport sans crasher ;
les 3 cas réels documentés en test_nonlinearity.py::TestRealWorldExamples
sont figés ici une seconde fois pour verrouiller la non-régression.
"""

import os

import pytest

from decision_core import generate_report, import_file
from decision_core.models import AnalysisConfig
from decision_core.reporting.warnings.constants import (
    MAX_NONLINEARITY_PAIRS,
    MAX_NONLINEARITY_WARNINGS,
)
from decision_core.stats.nonlinearity import (
    ETA_SQUARED_IMPROVEMENT_THRESHOLD,
    QUADRATIC_IMPROVEMENT_THRESHOLD,
    QUADRATIC_P_VALUE_THRESHOLD,
    detect_quadratic_pattern,
    detect_step_pattern,
)

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")

# 18 fichiers listés dans docs/RAPPORT_TESTS_DOMAINES.md §2
EXAMPLE_FILES = [
    "ventes_magasin_2025.csv",
    "rh_masse_salariale_2025.csv",
    "elevage_production_lait_2025.csv",
    "finance_tresorerie_2025.csv",
    "logistique_livraisons_2025.csv",
    "sante_clinique_2025.csv",
    "education_elearning_2025.csv",
    "immobilier_estimations_2025.csv",
    "industrie_maintenance_2025.csv",
    "hotellerie_reservations_2025.csv",
    "restauration_gastronomie_2025.csv",
    "assurance_sinistres_2025.csv",
    "energie_batiments_2025.csv",
    "marketing_digital_2025.csv",
    "saas_abonnements_2025.csv",
    "cybersecurite_incidents_2025.csv",
    "tourisme_frequentation_2025.csv",
    "agriculture_rendement_2025.csv",
]


class TestSeuilsP12Geles:
    """Les constantes P1.2 ne doivent bouger qu'avec une décision explicite."""

    def test_seuils_quadratiques_geles(self):
        assert QUADRATIC_IMPROVEMENT_THRESHOLD == pytest.approx(0.04)
        assert QUADRATIC_P_VALUE_THRESHOLD == pytest.approx(0.10)

    def test_seuil_paliers_gele(self):
        assert ETA_SQUARED_IMPROVEMENT_THRESHOLD == pytest.approx(0.02)

    def test_plafonds_non_linearite_geles(self):
        assert MAX_NONLINEARITY_PAIRS == 300
        assert MAX_NONLINEARITY_WARNINGS == 3


class TestExamplesNonRegression:
    """Chaque CSV d'example doit rester analysable sans régression."""

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_import_ne_crash_pas(self, filename):
        path = os.path.join(EXAMPLES_DIR, filename)
        assert os.path.exists(path), f"Fichier manquant : {path}"
        df = import_file(path)
        assert len(df) >= 99, f"{filename}: attendu >=99 lignes après enrichissement, got {len(df)}"
        assert len(df.columns) >= 5

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_generate_report_ne_crash_pas(self, filename):
        df = import_file(os.path.join(EXAMPLES_DIR, filename))
        report = generate_report(df, AnalysisConfig(iqr_k=1.5))
        # Contrat minimal du rapport — cf. docs/SPEC.md §4.9
        assert "dataset_summary" in report
        assert "warnings" in report
        assert "top_correlations" in report
        assert "exploitability" in report
        assert report["dataset_summary"]["n_rows"] == len(df)

    @pytest.mark.parametrize("filename", EXAMPLE_FILES)
    def test_report_est_deterministe(self, filename):
        """Deux appels successifs sur le même fichier donnent le même rapport."""
        path = os.path.join(EXAMPLES_DIR, filename)
        df = import_file(path)
        r1 = generate_report(df, AnalysisConfig(iqr_k=1.5))
        # Re-import pour éviter un effet de mutation
        df2 = import_file(path)
        r2 = generate_report(df2, AnalysisConfig(iqr_k=1.5))
        assert r1["warnings"] == r2["warnings"]
        assert r1["top_correlations"] == r2["top_correlations"]


class TestP12CasReelsGeles:
    """
    Verrouillage des 3 cas réels documentés en TestRealWorldExamples.
    Si un seuil P1.2 change, ces tests cassent — c'est voulu.
    """

    def test_energie_quadratique_non_retenu(self):
        # energie_batiments_2025.csv : Temperature_Exterieure_C -> Consommation_KWh
        # gain R² ≈0.005 < 0.04 et p≈0.30 > 0.10 → non retenu (CHANGELOG Unreleased)
        df = import_file(os.path.join(EXAMPLES_DIR, "energie_batiments_2025.csv"))
        assert detect_quadratic_pattern(df, "Consommation_KWh", "Temperature_Exterieure_C") is None

    def test_logistique_paliers_non_retenu(self):
        # logistique_livraisons_2025.csv : Poids_Colis_Kg -> Frais_Port_Euros
        # eta² - R² ≈0.006 < 0.02 sur n=149 → non retenu (dataset enrichi)
        df = import_file(os.path.join(EXAMPLES_DIR, "logistique_livraisons_2025.csv"))
        assert detect_step_pattern(df, "Frais_Port_Euros", "Poids_Colis_Kg") is None

    def test_agriculture_quadratique_retenu(self):
        # agriculture_rendement_2025.csv : Pluviometrie_Mm -> Rendement_Quintal_Ha
        # R² quad 0.184 vs lin -0.004, p≈8.5e-12 → retenu
        df = import_file(os.path.join(EXAMPLES_DIR, "agriculture_rendement_2025.csv"))
        result = detect_quadratic_pattern(df, "Rendement_Quintal_Ha", "Pluviometrie_Mm")
        assert result is not None
        assert result.p_value < 0.001
        assert result.r2_quadratic_adj > result.r2_linear_adj
