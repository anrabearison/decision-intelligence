"""
Tests du module de profiling.
Valeurs de référence calculées indépendamment (pandas en ligne de commande)
et vérifiées avant d'écrire le moteur, conformément au TDD.
"""
import os
import pandas as pd
import pytest
from decision_core.profiling import (
    descriptive_stats,
    correlation_matrix,
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    return pd.read_csv(os.path.join(FIXTURES_DIR, name))


class TestDescriptiveStatsVentes:
    def setup_method(self):
        self.df = load("ventes_test.csv")

    def test_prix_mean(self):
        stats = descriptive_stats(self.df["Prix"])
        assert stats["mean"] == pytest.approx(446.5, abs=0.01)

    def test_prix_std_dev(self):
        stats = descriptive_stats(self.df["Prix"])
        assert stats["std_dev"] == pytest.approx(367.11, abs=0.01)

    def test_prix_min_max(self):
        stats = descriptive_stats(self.df["Prix"])
        assert stats["min"] == 45
        assert stats["max"] == 870

    def test_ventes_mean(self):
        stats = descriptive_stats(self.df["Ventes"])
        assert stats["mean"] == pytest.approx(67.3, abs=0.01)


class TestCorrelationVentes:
    def test_prix_ventes_correlation(self):
        df = load("ventes_test.csv")
        corr = correlation_matrix(df)
        assert corr.loc["Prix", "Ventes"] == pytest.approx(-0.8877, abs=0.001)


class TestCorrelationTroupeau:
    def test_temperature_ventes_lait_correlation(self):
        df = load("troupeau_test.csv")
        corr = correlation_matrix(df)
        assert corr.loc["Temperature", "Ventes_lait"] == pytest.approx(-0.8845, abs=0.001)


class TestCorrelationTresorerie:
    def test_clients_solde_correlation(self):
        df = load("tresorerie_test.csv")
        corr = correlation_matrix(df)
        assert corr.loc["Nouveaux_clients", "Solde_fin_mois"] == pytest.approx(0.9782, abs=0.001)

    def test_revenus_solde_correlation(self):
        df = load("tresorerie_test.csv")
        corr = correlation_matrix(df)
        assert corr.loc["Revenus", "Solde_fin_mois"] == pytest.approx(0.9949, abs=0.001)


class TestCorrelationMatrixOnlyNumeric:
    def test_correlation_ignores_non_numeric_columns(self):
        df = load("ventes_test.csv")
        corr = correlation_matrix(df)
        assert "Produit" not in corr.columns
        assert "Ville" not in corr.columns
