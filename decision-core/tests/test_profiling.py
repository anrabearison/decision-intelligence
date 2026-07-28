"""
Tests du module de profiling.
Valeurs de référence calculées indépendamment (pandas en ligne de commande)
et vérifiées avant d'écrire le moteur, conformément au TDD.
"""
import os
import numpy as np
import pandas as pd
import pytest
from decision_core.profiling import (
    descriptive_stats,
    correlation_matrix,
    correlation_pvalues,
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


class TestMultipleComparisonsCorrection:
    def test_many_independent_columns_flags_few_or_no_significant_correlations(self):
        # Cas empirique trouvé en audit expert : avec 15 colonnes
        # indépendantes (aucune vraie relation) et n=30, la corrélation
        # "la plus forte" dépasse 0.4 dans 97% des cas par pur hasard
        # (problème des comparaisons multiples, jamais corrigé avant ce fix).
        # Après correction Benjamini-Hochberg, la quasi-totalité ne doit
        # plus être signalée comme significative.
        rng = np.random.default_rng(0)
        df = pd.DataFrame({f"V{i}": rng.normal(0, 1, 30) for i in range(15)})
        pairs = correlation_pvalues(df)
        n_significant = sum(1 for p in pairs if p["significant_after_correction"])
        # Sur du bruit pur, le taux de fausses découvertes visé est 5% -
        # tolérance large pour rester un test stable, pas un test de
        # précision exacte sur un tirage aléatoire unique.
        assert n_significant <= len(pairs) * 0.15

    def test_true_strong_relationship_remains_significant_after_correction(self):
        # La correction ne doit pas supprimer un vrai signal fort.
        rng = np.random.default_rng(1)
        x = rng.normal(0, 1, 40)
        y = 3 * x + rng.normal(0, 0.3, 40)
        df = pd.DataFrame({"X": x, "Y": y, "Bruit1": rng.normal(0, 1, 40), "Bruit2": rng.normal(0, 1, 40)})
        pairs = correlation_pvalues(df)
        xy_pair = next(p for p in pairs if {p["column_a"], p["column_b"]} == {"X", "Y"})
        assert xy_pair["significant_after_correction"] is True

    def test_returns_p_value_and_correction_fields(self):
        rng = np.random.default_rng(2)
        df = pd.DataFrame({"A": rng.normal(0, 1, 30), "B": rng.normal(0, 1, 30)})
        pairs = correlation_pvalues(df)
        assert len(pairs) == 1
        assert "p_value" in pairs[0]
        assert "significant_after_correction" in pairs[0]
        assert "value" in pairs[0]


class TestCorrelationPvaluesPerformanceCap:
    def test_caps_pairs_tested_above_column_limit(self):
        # Trouvé en audit expert : croissance quadratique du nombre de
        # paires (C(k,2)) - 200 colonnes = 19900 paires = ~34s, incompatible
        # avec un traitement synchrone HTTP. Plafond : au-delà de
        # MAX_COLUMNS_FOR_CORRELATION colonnes, seules les N premières
        # (déterministe) sont utilisées pour les corrélations - le reste
        # du rapport (profiling par colonne) reste peu coûteux et
        # continue de couvrir toutes les colonnes.
        rng = np.random.default_rng(0)
        n_cols = 80
        df = pd.DataFrame({f"V{i}": rng.normal(0, 1, 30) for i in range(n_cols)})
        pairs = correlation_pvalues(df)
        from decision_core.profiling import MAX_COLUMNS_FOR_CORRELATION
        expected_pairs = MAX_COLUMNS_FOR_CORRELATION * (MAX_COLUMNS_FOR_CORRELATION - 1) // 2
        assert len(pairs) == expected_pairs

    def test_no_cap_below_threshold(self):
        rng = np.random.default_rng(0)
        n_cols = 10
        df = pd.DataFrame({f"V{i}": rng.normal(0, 1, 30) for i in range(n_cols)})
        pairs = correlation_pvalues(df)
        assert len(pairs) == n_cols * (n_cols - 1) // 2
