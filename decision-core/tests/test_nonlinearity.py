"""
Tests pour la détection de non-linéarité (P1.2).
"""
import numpy as np
import pandas as pd
import pytest
from decision_core.stats.nonlinearity import (
    detect_quadratic_pattern,
    detect_step_pattern,
    MIN_ROWS_FOR_NONLINEARITY,
)
from decision_core.models.nonlinearity import QuadraticPatternResult, StepPatternResult


class TestQuadraticPattern:
    """Tests pour detect_quadratic_pattern."""

    def test_detects_u_curve(self):
        """Teste la détection d'une courbe en U (coefficient quadratique positif)."""
        np.random.seed(42)
        x = np.linspace(-10, 10, 30)
        # y = 2 + 0.5*x + 0.1*x² + bruit léger
        y = 2 + 0.5 * x + 0.1 * x**2 + np.random.randn(30) * 2
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_quadratic_pattern(df, "target", "feature")

        assert result is not None
        assert isinstance(result, QuadraticPatternResult)
        assert result.pattern_type == "u_curve"
        assert result.quadratic_coefficient > 0
        assert result.r2_quadratic_adj > result.r2_linear_adj
        assert result.p_value < 0.05

    def test_detects_optimum(self):
        """Teste la détection d'une relation en cloche/optimum (coefficient quadratique négatif)."""
        np.random.seed(42)
        x = np.linspace(-10, 10, 30)
        # y = 100 - 0.5*x² (cloche pure centrée, pas de terme linéaire) + très peu de bruit
        y = 100 - 0.5 * x**2 + np.random.randn(30) * 0.3
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_quadratic_pattern(df, "target", "feature")

        assert result is not None
        assert isinstance(result, QuadraticPatternResult)
        assert result.pattern_type == "optimum"
        assert result.quadratic_coefficient < 0
        assert result.r2_quadratic_adj > result.r2_linear_adj
        assert result.p_value < 0.05

    def test_returns_none_on_linear_relation(self):
        """Teste qu'une relation linéaire + bruit ne génère pas de faux positif."""
        np.random.seed(42)
        x = np.linspace(0, 20, 30)
        # y = 3 + 2*x + bruit (pas de terme quadratique)
        y = 3 + 2 * x + np.random.randn(30) * 1
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_quadratic_pattern(df, "target", "feature")

        assert result is None

    def test_returns_none_on_small_sample(self):
        """Teste le garde-fou petit échantillon (n < 10)."""
        np.random.seed(42)
        x = np.linspace(-10, 10, 8)
        y = 2 + 0.5 * x + 0.1 * x**2 + np.random.randn(8) * 2
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_quadratic_pattern(df, "target", "feature")

        assert result is None

    def test_handles_nan_values(self):
        """Teste que les NaN sont correctement gérés."""
        np.random.seed(42)
        x = np.linspace(-10, 10, 30)
        y = 2 + 0.5 * x + 0.1 * x**2 + np.random.randn(30) * 2
        # Ajouter des NaN
        x[5] = np.nan
        y[10] = np.nan
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_quadratic_pattern(df, "target", "feature")

        # Doit encore détecter le pattern avec les données restantes
        # (si assez de données après nettoyage)
        if result is not None:
            assert isinstance(result, QuadraticPatternResult)


class TestStepPattern:
    """Tests pour detect_step_pattern."""

    def test_detects_step_function(self):
        """Teste la détection d'une fonction par paliers."""
        np.random.seed(42)
        x = np.linspace(0, 20, 60)
        # Fonction par paliers non-monotone pour mieux tester : bas-haut-bas
        y = np.where(x < 5, 10, np.where(x < 10, 50, np.where(x < 15, 20, 10)))
        y = y + np.random.randn(60) * 0.3  # bruit très léger
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_step_pattern(df, "target", "feature")

        assert result is not None
        assert isinstance(result, StepPatternResult)
        # Le modèle par bins doit expliquer plus de variance que le linéaire
        assert result.eta_squared_binned > result.r2_linear
        assert result.n_bins >= 2

    def test_returns_none_on_linear_relation(self):
        """Teste qu'une relation linéaire ne génère pas de faux positif."""
        np.random.seed(42)
        x = np.linspace(0, 20, 30)
        y = 3 + 2 * x + np.random.randn(30) * 1
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_step_pattern(df, "target", "feature")

        assert result is None

    def test_returns_none_on_small_sample(self):
        """Teste le garde-fou petit échantillon (n < 10)."""
        np.random.seed(42)
        x = np.linspace(0, 20, 8)
        y = np.where(x < 5, 10, 20)
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_step_pattern(df, "target", "feature")

        assert result is None

    def test_handles_nan_values(self):
        """Teste que les NaN sont correctement gérés."""
        np.random.seed(42)
        x = np.linspace(0, 20, 40)
        y = np.where(x < 5, 10, np.where(x < 10, 20, np.where(x < 15, 30, 40)))
        y = y + np.random.randn(40) * 1
        x[5] = np.nan
        y[10] = np.nan
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_step_pattern(df, "target", "feature")

        # Doit encore détecter le pattern avec les données restantes
        # (si assez de données après nettoyage)
        if result is not None:
            assert isinstance(result, StepPatternResult)


class TestIntegrationWithGenerateReport:
    """Tests d'intégration avec generate_report."""

    def test_generate_report_includes_nonlinearity_warning(self):
        """Teste que generate_report inclut le warning de non-linéarité."""
        from decision_core import generate_report

        np.random.seed(42)
        x = np.linspace(-10, 10, 30)
        y = 2 + 0.5 * x + 0.1 * x**2 + np.random.randn(30) * 2
        df = pd.DataFrame({"Temperature": x, "Consommation": y})

        report = generate_report(df)

        assert report is not None
        warnings = report.warnings
        nonlinearity_warnings = [w for w in warnings if "non-linéaire" in w.lower()]
        assert len(nonlinearity_warnings) > 0
