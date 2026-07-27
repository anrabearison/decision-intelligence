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


class TestCorrelationMatrixExcludesIdentifiers:
    def test_correlation_ignores_identifier_columns(self):
        # Numero_lot est une séquence 1..n : numérique mais un identifiant,
        # jamais une variable explicative légitime dans une corrélation.
        # Temperature/Taux_defaut ont des valeurs répétées (contrairement à
        # Numero_lot) pour ne pas être elles-mêmes détectées comme identifiant.
        df = pd.DataFrame({
            "Numero_lot": range(1, 31),
            "Temperature": [70, 71, 70, 72, 71, 70, 73, 71, 70, 72] * 3,
            "Taux_defaut": [0.5, 0.6, 0.5, 0.7, 0.6, 0.5, 0.8, 0.6, 0.5, 0.7] * 3,
        })
        corr = correlation_matrix(df)
        assert "Numero_lot" not in corr.columns

    def test_correlation_keeps_legitimate_discrete_numeric_columns(self):
        # Un compteur/quantité discret légitime (pas un identifiant) doit
        # rester dans la matrice - seule l'identification stricte doit exclure.
        df = pd.DataFrame({
            "Quantite": [1, 2, 1, 3, 2, 1, 4, 2, 1, 3] * 3,
            "Prix": [10, 20, 10, 30, 20, 10, 40, 20, 10, 30] * 3,
        })
        corr = correlation_matrix(df)
        assert "Quantite" in corr.columns
