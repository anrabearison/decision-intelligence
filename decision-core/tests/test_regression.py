"""
Tests du module de régression (simple et multivariée) et de simulation.
Coefficients de référence calculés avec scipy.stats.linregress / numpy.linalg.lstsq
avant l'écriture du moteur (TDD).
"""
import os
import pandas as pd
import pytest
from decision_core.regression import fit_simple_regression, fit_multivariate_regression
from decision_core.simulation import simulate_scenario

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    return pd.read_csv(os.path.join(FIXTURES_DIR, name))


class TestSimpleRegressionVentes:
    def test_coefficients(self):
        df = load("ventes_test.csv")
        model = fit_simple_regression(df, target="Ventes", feature="Prix")
        assert model["slope"] == pytest.approx(-0.0959, abs=0.001)
        assert model["intercept"] == pytest.approx(110.118, abs=0.01)

    def test_r_squared(self):
        df = load("ventes_test.csv")
        model = fit_simple_regression(df, target="Ventes", feature="Prix")
        assert model["r_squared"] == pytest.approx(0.788, abs=0.001)


class TestSimpleRegressionTroupeau:
    def test_coefficients(self):
        df = load("troupeau_test.csv")
        model = fit_simple_regression(df, target="Ventes_lait", feature="Temperature")
        assert model["slope"] == pytest.approx(-8.564, abs=0.01)
        assert model["r_squared"] == pytest.approx(0.782, abs=0.001)


class TestMultivariateRegressionTresorerie:
    def test_coefficients(self):
        df = load("tresorerie_test.csv")
        model = fit_multivariate_regression(
            df, target="Solde_fin_mois", features=["Nouveaux_clients", "Charges_variables"]
        )
        assert model["intercept"] == pytest.approx(995.0, abs=0.5)
        assert model["coefficients"]["Nouveaux_clients"] == pytest.approx(594.09, abs=0.5)
        assert model["coefficients"]["Charges_variables"] == pytest.approx(-0.277, abs=0.01)


class TestSimulateScenarioRetail:
    def test_price_increase_5_percent_decreases_sales(self):
        df = load("ventes_test.csv")
        result = simulate_scenario(
            df, target="Ventes", feature="Prix", change_pct=0.05
        )
        # baseline = moyenne des Ventes observées
        assert result["baseline"] == pytest.approx(67.3, abs=0.01)
        # une hausse de prix doit faire baisser la prédiction (pente negative)
        assert result["simulated"] < result["baseline"]

    def test_returns_change_pct(self):
        df = load("ventes_test.csv")
        result = simulate_scenario(
            df, target="Ventes", feature="Prix", change_pct=0.05
        )
        expected_change_pct = (result["simulated"] - result["baseline"]) / result["baseline"] * 100
        assert result["change_pct"] == pytest.approx(expected_change_pct, abs=0.01)


class TestRegressionRejectsNonNumericFeature:
    def test_raises_on_categorical_feature(self):
        df = load("ventes_test.csv")
        with pytest.raises(TypeError):
            fit_simple_regression(df, target="Ventes", feature="Produit")
