"""
Tests pour la détection de non-linéarité (P1.2).
"""
import os

import numpy as np
import pandas as pd
import pytest
from decision_core.reporting.warnings import _build_nonlinearity_warnings
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
        assert result is not None
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
        # Fonction par paliers non-monotone pour que le R2 linéaire reste faible
        y = np.where(x < 5, 10, np.where(x < 10, 50, np.where(x < 15, 20, 10)))
        y = y + np.random.randn(40) * 0.3
        x[5] = np.nan
        y[10] = np.nan
        df = pd.DataFrame({"feature": x, "target": y})

        result = detect_step_pattern(df, "target", "feature")

        # Doit encore détecter le pattern avec les données restantes
        assert result is not None
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
        assert any("p ajustée" in w.lower() for w in nonlinearity_warnings)

    def test_real_world_ventes_magasin_satisfaction_client_pairs_do_not_duplicate_nonlinearity_warnings(self):
        from decision_core.importer import import_file

        examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")
        df = import_file(os.path.join(examples_dir, "ventes_magasin_2025.csv"))

        # Vérification préalable : sur n=363, le signal non-linéaire Satisfaction/CA n'est plus détecté
        # Résultat réel : detect_quadratic_pattern = None, detect_step_pattern = None
        # Les données plus nombreuses et variées rendent la relation moins clairement quadratique
        # Comportement attendu : aucun warning non-linéaire sur cette paire
        
        warnings = []
        top_correlations = [
            {"column_a": "Satisfaction_Client", "column_b": "Chiffre_Affaires", "value": 1.0},
            {"column_a": "Satisfaction_Client", "column_b": "Quantite_Vendue", "value": 1.0},
        ]
        _build_nonlinearity_warnings(df, ["Satisfaction_Client", "Chiffre_Affaires", "Quantite_Vendue"], top_correlations, warnings)

        ca_warnings = [w for w in warnings if "Chiffre_Affaires" in w and "Satisfaction_Client" in w]
        q_warnings = [w for w in warnings if "Quantite_Vendue" in w and "Satisfaction_Client" in w]

        # Sur n=363, aucun pattern non-linéaire détecté sur ces paires
        assert len(ca_warnings) == 0
        assert len(q_warnings) == 0

    def test_generate_report_emits_step_warning_when_step_pattern_only(self):
        from decision_core import generate_report

        # Use a deterministic step-only dataset that is recognized by the detector
        x = np.linspace(0, 20, 60)
        levels = [49.94235033, 7.47241523, 43.40630287, 8.12464673]
        cuts = [7, 32, 43]
        y = np.empty_like(x)
        prev = 0
        for level, cut in zip(levels, cuts + [len(x)]):
            y[prev:cut] = level
            prev = cut
        rng = np.random.RandomState(0)
        y = y + rng.randn(60) * 0.4
        df = pd.DataFrame({"feature": x, "target": y})

        report = generate_report(df)
        step_warnings = [w for w in report.warnings if "paliers" in w.lower()]
        quadratic_warnings = [w for w in report.warnings if "optimum" in w.lower() or "courbe en u" in w.lower()]

        assert len(step_warnings) >= 1
        assert len(quadratic_warnings) == 0

    def test_generate_report_prefers_quadratic_over_step_when_both_signals_exist(self):
        from decision_core import generate_report

        np.random.seed(42)
        x = np.linspace(0, 20, 80)
        y = 20 - 0.5 * (x - 10) ** 2 + np.random.randn(80) * 0.2
        df = pd.DataFrame({"feature": x, "target": y})

        report = generate_report(df)
        step_warnings = [w for w in report.warnings if "paliers" in w]
        quadratic_warnings = [w for w in report.warnings if "optimum" in w or "courbe en U" in w]

        assert len(step_warnings) == 0
        assert len(quadratic_warnings) == 1

    def test_generate_report_scans_nonlinearity_beyond_top_linear_correlations(self):
        from decision_core import generate_report

        rng = np.random.default_rng(42)
        n = 60
        x = np.linspace(-10, 10, n)
        # Relation en cloche très forte mais corrélation linéaire proche de zéro.
        y = 100 - 0.8 * x**2 + rng.normal(0, 0.5, n)

        base = np.linspace(0, 100, n)
        df = pd.DataFrame({
            "Redondance_A": base,
            "Redondance_B": base * 1.01 + rng.normal(0, 0.01, n),
            "Redondance_C": base * 0.99 + rng.normal(0, 0.01, n),
            "Redondance_D": base + rng.normal(0, 0.01, n),
            "Redondance_E": base * 1.02 + rng.normal(0, 0.01, n),
            "Effort": x,
            "Performance": y,
        })

        report = generate_report(df)
        warnings = report.warnings

        assert any(
            "non-linéaire" in w.lower()
            and "Effort" in w
            and "Performance" in w
            for w in warnings
        )

    def test_nonlinearity_warnings_are_limited_to_highest_explanatory_gains(self):
        rng = np.random.default_rng(42)
        n = 80
        data = {}
        candidates = []

        for idx, strength in enumerate([1.0, 0.8, 0.6, 0.4], start=1):
            feature = f"feature_{idx}"
            target = f"target_{idx}"
            x = np.linspace(-10, 10, n)
            y = 100 - strength * x**2 + rng.normal(0, 0.2, n)
            data[feature] = x
            data[target] = y
            candidates.append({"column_a": feature, "column_b": target, "value": 0.0})

        df = pd.DataFrame(data)
        warnings = []

        patterns, _ = _build_nonlinearity_warnings(
            df,
            list(df.columns),
            [],
            warnings,
            candidate_correlations=candidates,
            max_warnings=3,
        )

        nonlinearity_warnings = [w for w in warnings if "non-linéaire" in w.lower()]
        assert len(patterns) == 4
        assert len(nonlinearity_warnings) == 3
        assert any("feature_1" in w and "target_1" in w for w in nonlinearity_warnings)
        assert not any("feature_4" in w and "target_4" in w for w in nonlinearity_warnings)


class TestRealWorldExamples:
    """Tests d'intégration sur les véritables jeux de données d'exemples."""

    def test_real_world_energy_quadratic_pattern(self):
        """Teste le cas réel #13 (Énergie) : Temperature_Exterieure_C -> Consommation_KWh."""
        import os
        from decision_core.importer import import_file
        
        examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")
        df = import_file(os.path.join(examples_dir, "energie_batiments_2025.csv"))
        
        result = detect_quadratic_pattern(df, "Consommation_KWh", "Temperature_Exterieure_C")
        
        # Avec les seuils quadratiques recalibrés (gain R² ajusté +0.04, p ≤ 0.10),
        # ce signal faible n'est plus retenu malgré un p-value brute proche de 0.30.
        assert result is None

    def test_real_world_logistics_step_pattern(self):
        """Teste le cas réel #5 (Logistique) : Poids_Colis_Kg -> Frais_Port_Euros."""
        import os
        from decision_core.importer import import_file
        
        examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")
        df = import_file(os.path.join(examples_dir, "logistique_livraisons_2025.csv"))
        
        # Vérification préalable : sur n=149, le signal paliers se dilue
        # Dataset enrichi : 149 lignes vs 15 avant
        # Résultat réel : eta²=0.534, R²_lin=0.528, diff=0.006 < seuil 0.02
        # Comportement attendu et documenté : limite connue de P1.2 sur données réelles multi-variées
        result = detect_step_pattern(df, "Frais_Port_Euros", "Poids_Colis_Kg")
        
        # Sur n=149, le pattern paliers n'est plus détecté statistiquement
        # (la ligne droite s'ajuste presque aussi bien que les bins)
        assert result is None  # Signal dilué sous le seuil de détection

    def test_real_world_agriculture_quadratic_pattern(self):
        """Teste le cas réel #18 (Agriculture) : Pluviometrie_Mm -> Rendement_Quintal_Ha."""
        import os
        from decision_core.importer import import_file
        
        examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "examples")
        df = import_file(os.path.join(examples_dir, "agriculture_rendement_2025.csv"))
        
        # Vérification préalable : sur n=223 avec 4 variables numériques
        # Résultat réel : R²_quadratic=0.184, R²_linear=-0.004, p=8.5e-12
        # La pluviométrie seule explique ~18% du rendement (pas 80%+ comme sur n=15)
        # Ce qui est statistiquement cohérent avec un modèle multi-facteurs
        result = detect_quadratic_pattern(df, "Rendement_Quintal_Ha", "Pluviometrie_Mm")
        
        # Le pattern est encore détecté (p très significatif)
        assert result is not None
        assert isinstance(result, QuadraticPatternResult)
        assert result.pattern_type == "optimum"
        # Le modèle quadratique explique mieux que le linéaire
        assert result.r2_quadratic_adj > result.r2_linear_adj
        # p-value très significative confirme le pattern
        assert result.p_value < 0.001
        assert result.p_value < 0.05
