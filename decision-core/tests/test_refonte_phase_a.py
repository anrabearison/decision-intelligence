"""
Tests pour les nouvelles fonctionnalités de refonte Phase A.
Couvre R2 (baseline configurable), R4 (bornes simulation),
R7 (seuil IQR configurable), R8 (warning saisonnalité),
R9 (score d'exploitabilité).
"""
import pandas as pd
import pytest

from decision_core.simulation import simulate_scenario
from decision_core.anomaly_detection import detect_anomalies_iqr
from decision_core.models import SimulationConfig, AnalysisConfig

from decision_core.report import (
    generate_report,
    _detect_temporal_columns,
    _compute_exploitability_score,
)


# ---------------------------------------------------------------------------
# Tests Dataclasses de Configuration (POO)
# ---------------------------------------------------------------------------

class TestDataclassesConfig:
    def test_simulation_config_valid_bounds(self):
        """SimulationConfig doit s'instancier correctement avec des bornes valides."""
        config = SimulationConfig(target="Y", feature="X", change_pct=0.10, bounds=(0.0, 100.0))
        assert config.bounds == (0.0, 100.0)

    def test_simulation_config_invalid_bounds_raises_error(self):
        """SimulationConfig doit lever ValueError si min_val > max_val."""
        with pytest.raises(ValueError, match="bounds invalides"):
            SimulationConfig(target="Y", feature="X", change_pct=0.10, bounds=(100.0, 0.0))

    def test_analysis_config_valid_iqr_k(self):
        """AnalysisConfig doit s'instancier avec son paramètre iqr_k par défaut (1.5)."""
        config = AnalysisConfig()
        assert config.iqr_k == 1.5

    def test_analysis_config_invalid_iqr_k_raises_error(self):
        """AnalysisConfig doit lever ValueError si iqr_k <= 0."""
        with pytest.raises(ValueError, match="iqr_k doit être strictement supérieur à 0"):
            AnalysisConfig(iqr_k=0.0)
        with pytest.raises(ValueError, match="iqr_k doit être strictement supérieur à 0"):
            AnalysisConfig(iqr_k=-1.5)



# ---------------------------------------------------------------------------
# Fixtures communes
# ---------------------------------------------------------------------------

def _make_linear_df(n=40):
    """Dataset propre à relation linéaire forte pour les tests de simulation."""
    import numpy as np
    rng = np.random.default_rng(42)
    x = rng.uniform(10, 100, n)
    y = 2.5 * x + rng.normal(0, 5, n)
    return pd.DataFrame({"Feature": x, "Target": y})


def _make_sales_df():
    """Dataset PME avec remises promo (potentiels faux positifs IQR)."""
    rows = []
    for i in range(50):
        remise = 0.0
        if i % 10 == 0:
            remise = 5.0   # remise promo normale
        elif i % 15 == 0:
            remise = 10.0  # remise promo normale
        rows.append({"Semaine": i + 1, "CA": 2000 + i * 10, "Remise_Pct": remise})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# R2 — Baseline configurable
# ---------------------------------------------------------------------------

class TestBaselineConfigurable:
    """R2 : simulate_scenario doit accepter un baseline_feature_value optionnel."""

    def test_default_baseline_uses_mean(self):
        """Sans baseline_feature_value, la moyenne historique de la feature
        est utilisée comme point de départ (comportement par défaut inchangé)."""
        from decision_core.regression import fit_simple_regression
        df = _make_linear_df()
        model = fit_simple_regression(df, "Target", "Feature")
        expected_baseline = model.intercept + model.slope * float(df["Feature"].mean())
        result = simulate_scenario(df, "Target", "Feature", 0.10)
        assert result.baseline == pytest.approx(expected_baseline, rel=1e-9)

    def test_custom_baseline_overrides_mean(self):
        """Avec baseline_feature_value, la valeur fournie remplace la moyenne.
        Test déterministe : on utilise une valeur fixe connue loin de la moyenne.
        """
        from decision_core.regression import fit_simple_regression
        df = _make_linear_df()
        # Valeur fixée volontairement éloignée de la moyenne (≈55) : Feature ∈ [10, 100]
        custom_value = 10.0
        model = fit_simple_regression(df, "Target", "Feature")
        expected_custom_baseline = model.intercept + model.slope * custom_value
        expected_mean_baseline = model.intercept + model.slope * float(df["Feature"].mean())

        result = simulate_scenario(df, "Target", "Feature", 0.10, baseline_feature_value=custom_value)

        assert result.baseline == pytest.approx(expected_custom_baseline, rel=1e-9)
        assert result.baseline != pytest.approx(expected_mean_baseline, rel=1e-3)

    def test_custom_baseline_at_zero_is_accepted(self):
        """Une baseline_feature_value de 0.0 est acceptée sans exception.
        Le résultat est mathématiquement correct (simulated = intercept)."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", 0.10, baseline_feature_value=0.0
        )
        assert result.baseline is not None
        assert result.feature == "Feature"
        # simulated_feature = 0.0 * (1 + 0.10) = 0.0 → égal à la baseline
        assert result.simulated == pytest.approx(result.baseline, rel=1e-9)

    def test_simulation_config_dict_supports_baseline(self):
        """generate_report doit passer baseline_feature_value depuis simulation_config."""
        df = _make_linear_df()
        last_val = float(df["Feature"].iloc[-1])
        report = generate_report(
            df,
            simulation_config={
                "target": "Target",
                "feature": "Feature",
                "change_pct": 0.10,
                "baseline_feature_value": last_val,
            },
        )
        assert "simulation" in report
        assert report["simulation"]["feature"] == "Feature"


# ---------------------------------------------------------------------------
# R4 — Bornes physiques / institutionnelles
# ---------------------------------------------------------------------------

class TestBornesSimulation:
    """R4 : simulate_scenario doit clipper le résultat simulé aux bornes fournies."""

    def test_bounds_clip_simulated_above_max(self):
        """Un résultat simulé > max_val doit être clippé à max_val."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", 5.0, bounds=(0.0, 20.0)
        )
        assert result.simulated <= 20.0

    def test_bounds_clip_simulated_below_min(self):
        """Un résultat simulé < min_val doit être clippé à min_val."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", -1.0, bounds=(0.0, 500.0)
        )
        assert result.simulated >= 0.0

    def test_bounds_applied_flag_true_when_clipped(self):
        """bounds_applied doit être True quand le résultat a été clippé."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", 50.0, bounds=(0.0, 1.0)
        )
        assert result.bounds_applied is True

    def test_bounds_applied_flag_false_when_not_clipped(self):
        """bounds_applied doit être False quand le résultat est dans les bornes."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", 0.001, bounds=(0.0, 99999.0)
        )
        assert result.bounds_applied is False

    def test_no_bounds_key_absent_from_result(self):
        """Sans bounds, la clé 'bounds_applied' ne doit pas apparaître ou être None."""
        df = _make_linear_df()
        result = simulate_scenario(df, "Target", "Feature", 0.10)
        assert result.bounds_applied is None

    def test_bounds_inverted_raises_value_error(self):
        """bounds=(max, min) avec min > max doit lever ValueError immédiatement.
        Un appel silencieux avec des bornes inversées produirait toujours
        la même valeur (max_val = 0) quelle que soit l'entrée."""
        df = _make_linear_df()
        with pytest.raises(ValueError, match="bounds invalides"):
            simulate_scenario(df, "Target", "Feature", 0.10, bounds=(100.0, 0.0))

    def test_simulation_config_dict_supports_bounds(self):
        """generate_report doit passer bounds depuis simulation_config."""
        df = _make_linear_df()
        report = generate_report(
            df,
            simulation_config={
                "target": "Target",
                "feature": "Feature",
                "change_pct": 50.0,
                "bounds": (0.0, 1.0),
            },
        )
        assert report["simulation"]["simulated"] <= 1.0


# ---------------------------------------------------------------------------
# R7 — Seuil IQR configurable
# ---------------------------------------------------------------------------

class TestSeuilIQRConfigurable:
    """R7 : le multiplicateur k de l'IQR est configurable via analysis_config."""

    def test_default_k_preserved(self):
        """k=1.5 par défaut — le comportement existant est inchangé."""
        series = pd.Series([1.0, 2.0, 2.0, 2.5, 3.0, 100.0])  # 100 est une anomalie
        result_default = detect_anomalies_iqr(series)
        result_k15 = detect_anomalies_iqr(series, k=1.5)
        assert result_default.indices == result_k15.indices

    def test_higher_k_fewer_anomalies(self):
        """Un k plus élevé doit produire moins d'anomalies (bornes plus larges)."""
        series = pd.Series([1.0] * 30 + [10.0])
        result_strict = detect_anomalies_iqr(series, k=1.5)
        result_lax = detect_anomalies_iqr(series, k=3.0)
        assert len(result_lax.indices) <= len(result_strict.indices)


    def test_iqr_k_via_analysis_config(self):
        """generate_report doit lire iqr_k depuis analysis_config (et non
        simulation_config) — séparation de responsabilités."""
        df = _make_sales_df()
        # k très élevé → presque aucune anomalie (bornes très larges)
        report_lax = generate_report(
            df,
            simulation_config={"target": "CA", "feature": "Semaine", "change_pct": 0.1},
            analysis_config={"iqr_k": 10.0},
        )
        # k très strict → plus d'anomalies potentielles
        report_strict = generate_report(
            df,
            simulation_config={"target": "CA", "feature": "Semaine", "change_pct": 0.1},
            analysis_config={"iqr_k": 0.5},
        )
        n_lax = sum(len(a["indices"]) for a in report_lax["anomalies"].values())
        n_strict = sum(len(a["indices"]) for a in report_strict["anomalies"].values())
        assert n_lax <= n_strict

    def test_iqr_k_default_without_any_config(self):
        """Sans simulation_config ni analysis_config, k=1.5 est utilisé
        (compatibilité ascendante totale)."""
        df = _make_sales_df()
        report = generate_report(df)
        assert "anomalies" in report

    def test_iqr_k_not_read_from_simulation_config(self):
        """iqr_k dans simulation_config ne doit PAS affecter la détection d'anomalies
        (séparation de responsabilités : simulation_config ne contrôle pas l'IQR)."""
        df = _make_sales_df()
        # Si iqr_k était lu depuis simulation_config, k=0.0001 produirait des
        # anomalies partout ; avec k lu depuis analysis_config uniquement,
        # ce paramètre est ignoré et k=1.5 s'applique.
        report_with_fake_iqr = generate_report(
            df,
            simulation_config={
                "target": "CA", "feature": "Semaine",
                "change_pct": 0.1, "iqr_k": 0.0001,  # ne doit pas être lu
            },
        )
        report_default = generate_report(
            df,
            simulation_config={"target": "CA", "feature": "Semaine", "change_pct": 0.1},
        )
        assert report_with_fake_iqr["anomalies"] == report_default["anomalies"]


# ---------------------------------------------------------------------------
# R8 — Warning saisonnalité
# ---------------------------------------------------------------------------

class TestWarningSaisonnalite:
    """R8 : un warning doit être émis quand une colonne temporelle est détectée
    et que des corrélations fortes existent."""

    def test_detect_temporal_columns_by_keyword(self):
        """_detect_temporal_columns détecte les colonnes dont le nom contient
        un mot-clé temporel comme mot entier (pas en sous-chaîne)."""
        df = pd.DataFrame({
            "Semaine": range(10),
            "Prix": range(10),
            "CA": range(10),
        })
        temporal = _detect_temporal_columns(df)
        assert "Semaine" in temporal
        assert "Prix" not in temporal
        assert "CA" not in temporal

    def test_detect_temporal_columns_case_insensitive(self):
        """La détection est insensible à la casse."""
        df = pd.DataFrame({"DATE_VENTE": [], "MOIS": [], "Revenue": []})
        temporal = _detect_temporal_columns(df)
        assert "DATE_VENTE" in temporal
        assert "MOIS" in temporal
        assert "Revenue" not in temporal

    def test_detect_temporal_columns_no_false_positive_bonjour(self):
        """'Bonjour' contient 'jour' en sous-chaîne mais n'est PAS temporel.
        La détection par mot entier évite ce faux positif."""
        df = pd.DataFrame({"Bonjour": [], "Montant": []})
        temporal = _detect_temporal_columns(df)
        assert "Bonjour" not in temporal

    def test_detect_temporal_columns_camelcase(self):
        """Les colonnes CamelCase sont correctement découpées.
        'DateVente' → {'date', 'vente'} → détecté comme temporel."""
        df = pd.DataFrame({"DateVente": [], "PrixUnitaire": []})
        temporal = _detect_temporal_columns(df)
        assert "DateVente" in temporal
        assert "PrixUnitaire" not in temporal

    def test_no_temporal_warning_without_temporal_column(self):
        """Sans colonne temporelle, aucun warning de saisonnalité."""
        df = pd.DataFrame({
            "Prix": [1.0, 2.0, 3.0, 4.0, 5.0] * 8,
            "Ventes": [10.0, 20.0, 30.0, 40.0, 50.0] * 8,
        })
        report = generate_report(df)
        assert not any("temporelle" in w.lower() or "saisonn" in w.lower()
                       for w in report["warnings"])

    def test_temporal_warning_emitted_with_strong_correlation(self):
        """Avec une colonne temporelle ET une forte corrélation, le warning est émis."""
        n = 40
        # Semaine corrélée parfaitement avec CA
        df = pd.DataFrame({
            "Semaine": list(range(1, n + 1)),
            "Prix": [10.0 + i * 0.1 for i in range(n)],   # corrélé avec Semaine
            "CA": [100.0 + i * 5 for i in range(n)],       # corrélé avec Semaine
        })
        report = generate_report(df)
        assert any("temporelle" in w.lower() or "saisonn" in w.lower()
                   for w in report["warnings"])

    def test_temporal_warning_absent_when_no_strong_correlation(self):
        """Colonne temporelle présente mais pas de corrélation forte → pas de warning."""
        import numpy as np
        rng = np.random.default_rng(0)
        n = 40
        df = pd.DataFrame({
            "Semaine": list(range(1, n + 1)),
            "Bruit": rng.normal(0, 1, n),  # aucune corrélation
        })
        report = generate_report(df)
        assert not any("temporelle" in w.lower() or "saisonn" in w.lower()
                       for w in report["warnings"])


# ---------------------------------------------------------------------------
# R9 — Score d'exploitabilité
# ---------------------------------------------------------------------------

class TestScoreExploitabilite:
    """R9 : generate_report doit inclure un champ 'exploitability' avec level et summary."""

    def test_exploitability_key_present_in_report(self):
        """Le champ 'exploitability' est toujours présent dans le rapport."""
        df = _make_linear_df()
        report = generate_report(df)
        assert "exploitability" in report
        assert "level" in report["exploitability"]
        assert "score" in report["exploitability"]
        assert "summary" in report["exploitability"]

    def test_green_level_for_clean_large_dataset(self):
        """Un dataset propre et large doit obtenir le niveau 'green'."""
        df = _make_linear_df(n=60)
        report = generate_report(df)
        assert report["exploitability"]["level"] == "green"

    def test_red_level_for_tiny_dataset(self):
        """Un dataset de moins de 15 lignes ne doit pas obtenir le niveau 'green'."""
        df = pd.DataFrame({"A": [1.0, 2.0, 3.0], "B": [4.0, 5.0, 6.0]})
        report = generate_report(df)
        # Petit dataset → jamais green (trop risqué pour un décideur)
        assert report["exploitability"]["level"] != "green"


    def test_score_is_integer_between_0_and_100(self):
        """Le score est un entier entre 0 et 100."""
        df = _make_linear_df()
        report = generate_report(df)
        score = report["exploitability"]["score"]
        assert 0 <= score <= 100

    def test_compute_exploitability_score_logic(self):
        """_compute_exploitability_score retourne les niveaux attendus."""
        green = _compute_exploitability_score(50, 0, 0, 0.9)
        assert green.level == "green"

        red = _compute_exploitability_score(5, 5, 3, 0.05)
        assert red.level == "red"

    def test_low_r_squared_downgrades_score(self):
        """Un R² très faible pénalise le score d'exploitabilité."""
        good = _compute_exploitability_score(50, 1, 0, 0.9)
        bad = _compute_exploitability_score(50, 1, 0, 0.02)
        assert bad.score < good.score
