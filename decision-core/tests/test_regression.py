"""
Tests du module de régression (simple et multivariée) et de simulation.
Coefficients de référence calculés avec scipy.stats.linregress / numpy.linalg.lstsq
avant l'écriture du moteur (TDD).
"""
import os
import numpy as np
import pandas as pd
import pytest
from decision_core.regression import (
    fit_simple_regression,
    fit_multivariate_regression,
    InsufficientDataError,
)
from decision_core.simulation import simulate_scenario

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    return pd.read_csv(os.path.join(FIXTURES_DIR, name))


class TestSimpleRegressionVentes:
    def test_coefficients(self):
        df = load("ventes_test.csv")
        model = fit_simple_regression(df, target="Ventes", feature="Prix")
        assert model.slope == pytest.approx(-0.0959, abs=0.001)
        assert model.intercept == pytest.approx(110.118, abs=0.01)

    def test_r_squared(self):
        df = load("ventes_test.csv")
        model = fit_simple_regression(df, target="Ventes", feature="Prix")
        assert model.r_squared == pytest.approx(0.788, abs=0.001)


class TestSimpleRegressionTroupeau:
    def test_coefficients(self):
        df = load("troupeau_test.csv")
        model = fit_simple_regression(df, target="Ventes_lait", feature="Temperature")
        assert model.slope == pytest.approx(-8.564, abs=0.01)
        assert model.r_squared == pytest.approx(0.782, abs=0.001)


class TestMultivariateRegressionTresorerie:
    def test_coefficients(self):
        df = load("tresorerie_test.csv")
        model = fit_multivariate_regression(
            df, target="Solde_fin_mois", features=["Nouveaux_clients", "Charges_variables"]
        )
        assert model.intercept == pytest.approx(995.0, abs=0.5)
        assert model.coefficients["Nouveaux_clients"] == pytest.approx(594.09, abs=0.5)
        assert model.coefficients["Charges_variables"] == pytest.approx(-0.277, abs=0.01)


class TestMultivariateRegressionDetectsMulticollinearity:
    def test_warns_on_near_perfect_collinear_features(self):
        np.random.seed(1)
        n = 40
        charges_a = np.random.uniform(100, 1000, n)
        charges_b = charges_a * 2.001 + np.random.normal(0, 0.01, n)
        y = 50 + 0.01 * charges_a + np.random.normal(0, 5, n)
        df = pd.DataFrame({"Charges_A": charges_a, "Charges_B": charges_b, "Y": y})
        model = fit_multivariate_regression(df, target="Y", features=["Charges_A", "Charges_B"])
        assert model.condition_number > 100
        assert model.multicollinearity_warning is True

    def test_no_warning_on_independent_features(self):
        np.random.seed(2)
        n = 40
        a = np.random.uniform(100, 1000, n)
        b = np.random.uniform(50, 500, n)  # indépendant de a
        y = 50 + 0.01 * a + 0.02 * b + np.random.normal(0, 5, n)
        df = pd.DataFrame({"A": a, "B": b, "Y": y})
        model = fit_multivariate_regression(df, target="Y", features=["A", "B"])
        assert model.condition_number < 30
        assert model.multicollinearity_warning is False


class TestSimulateScenarioRetail:
    def test_price_increase_5_percent_decreases_sales(self):
        df = load("ventes_test.csv")
        result = simulate_scenario(
            df, target="Ventes", feature="Prix", change_pct=0.05
        )
        # baseline = moyenne des Ventes observées
        assert result.baseline == pytest.approx(67.3, abs=0.01)
        # une hausse de prix doit faire baisser la prédiction (pente negative)
        assert result.simulated < result.baseline

    def test_returns_change_pct(self):
        df = load("ventes_test.csv")
        result = simulate_scenario(
            df, target="Ventes", feature="Prix", change_pct=0.05
        )
        expected_change_pct = (result.simulated - result.baseline) / result.baseline * 100
        assert result.change_pct == pytest.approx(expected_change_pct, abs=0.01)


class TestSimulateScenarioNearZeroBaseline:
    def test_change_pct_unreliable_when_baseline_near_zero(self):
        df = pd.DataFrame({
            "X": list(range(1, 21)),
            "Y": [9.45, 2.68, 0.98, -8.82, -0.88, -1.27, 0.09, -2.63, 0.28, -1.88,
                  -6.07, 4.93, 4.91, 9.05, 0.75, -1.52, -2.22, -7.23, 5.41, -5.0],
        })
        result = simulate_scenario(df, target="Y", feature="X", change_pct=0.1)
        assert result.change_pct_reliable is False
        assert result.change_pct is None

    def test_change_pct_reliable_when_baseline_not_near_zero(self):
        df = load("ventes_test.csv")
        result = simulate_scenario(df, target="Ventes", feature="Prix", change_pct=0.05)
        assert result.change_pct_reliable is True
        assert result.change_pct is not None


class TestSimulateScenarioPropagatesInsufficientData:
    def test_raises_on_constant_feature(self):
        df = pd.DataFrame({"X": [10.0] * 20, "Y": list(range(20))})
        with pytest.raises(InsufficientDataError):
            simulate_scenario(df, target="Y", feature="X", change_pct=0.1)

    def test_raises_on_single_row(self):
        df = pd.DataFrame({"X": [10], "Y": [20]})
        with pytest.raises(InsufficientDataError):
            simulate_scenario(df, target="Y", feature="X", change_pct=0.1)


class TestRegressionRejectsNonNumericFeature:
    def test_raises_on_categorical_feature(self):
        df = load("ventes_test.csv")
        with pytest.raises(TypeError):
            fit_simple_regression(df, target="Ventes", feature="Produit")


class TestRegressionHandlesMissingValues:
    def test_simple_regression_drops_nan_rows_and_computes_correctly(self):
        df = pd.DataFrame({
            "X": [1, 2, 3, 4, 5, None, 7, 8],
            "Y": [2, 4, 6, 8, 10, 12, None, 16],
        })
        model = fit_simple_regression(df, target="Y", feature="X")
        assert model.slope == pytest.approx(2.0, abs=0.01)
        assert not (model.slope != model.slope)  # pas NaN

    def test_multivariate_regression_drops_nan_rows(self):
        df = pd.DataFrame({
            "A": [1, 2, 3, 4, None, 6, 7, 8, 9, 10],
            "B": [1, 1, 2, 2, 3, 3, 4, 4, 5, 5],
            "Y": [10, 12, 14, 16, 18, None, 22, 24, 26, 28],
        })
        model = fit_multivariate_regression(df, target="Y", features=["A", "B"])
        assert model.r_squared == model.r_squared  # pas NaN


    def test_raises_insufficient_data_error_when_too_few_rows_after_dropna(self):
        df = pd.DataFrame({"X": [1, None, None, None], "Y": [2, None, None, 8]})
        with pytest.raises(InsufficientDataError):
            fit_simple_regression(df, target="Y", feature="X")


class TestRegressionHandlesZeroVariance:
    def test_raises_insufficient_data_error_on_constant_feature(self):
        df = pd.DataFrame({"X": [10.0] * 20, "Y": [1, 2, 3, 4, 5] * 4})
        with pytest.raises(InsufficientDataError):
            fit_simple_regression(df, target="Y", feature="X")

    def test_raises_insufficient_data_error_on_constant_target(self):
        df = pd.DataFrame({"X": [1, 2, 3, 4, 5] * 4, "Y": [7.0] * 20})
        with pytest.raises(InsufficientDataError):
            fit_simple_regression(df, target="Y", feature="X")


class TestRegressionHandlesTooFewRows:
    def test_raises_insufficient_data_error_on_single_row(self):
        df = pd.DataFrame({"X": [10], "Y": [20]})
        with pytest.raises(InsufficientDataError):
            fit_simple_regression(df, target="Y", feature="X")

    def test_raises_insufficient_data_error_below_min_rows_multivariate(self):
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4], "Y": [5, 6]})
        with pytest.raises(InsufficientDataError):
            fit_multivariate_regression(df, target="Y", features=["A", "B"])
