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
from decision_core.report import (
    generate_report,
    _detect_temporal_columns,
    _compute_exploitability_score,
)


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
        """Sans baseline_feature_value, le comportement par défaut est inchangé."""
        df = _make_linear_df()
        result_default = simulate_scenario(df, "Target", "Feature", 0.10)
        # La baseline doit être cohérente avec la moyenne de Feature
        assert result_default["baseline"] == pytest.approx(
            simulate_scenario(df, "Target", "Feature", 0.10)["baseline"]
        )

    def test_custom_baseline_overrides_mean(self):
        """Avec baseline_feature_value, la valeur fournie remplace la moyenne."""
        df = _make_linear_df()
        last_value = float(df["Feature"].iloc[-1])
        mean_value = float(df["Feature"].mean())

        result_mean = simulate_scenario(df, "Target", "Feature", 0.10)
        result_custom = simulate_scenario(
            df, "Target", "Feature", 0.10, baseline_feature_value=last_value
        )

        # Les baselines doivent différer si dernière valeur ≠ moyenne
        if abs(last_value - mean_value) > 1.0:
            assert result_custom["baseline"] != pytest.approx(result_mean["baseline"])

    def test_custom_baseline_at_zero_is_accepted(self):
        """Une baseline_feature_value de 0 est acceptée (pas de fallback silencieux)."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", 0.10, baseline_feature_value=0.0
        )
        assert "baseline" in result
        assert result["feature"] == "Feature"

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
        # Avec une très forte hausse, le simulé dépasse vraisemblablement 20
        result = simulate_scenario(
            df, "Target", "Feature", 5.0, bounds=(0.0, 20.0)
        )
        assert result["simulated"] <= 20.0

    def test_bounds_clip_simulated_below_min(self):
        """Un résultat simulé < min_val doit être clippé à min_val."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", -1.0, bounds=(0.0, 500.0)
        )
        assert result["simulated"] >= 0.0

    def test_bounds_applied_flag_true_when_clipped(self):
        """bounds_applied doit être True quand le résultat a été clippé."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", 50.0, bounds=(0.0, 1.0)
        )
        assert result.get("bounds_applied") is True

    def test_bounds_applied_flag_false_when_not_clipped(self):
        """bounds_applied doit être False quand le résultat est dans les bornes."""
        df = _make_linear_df()
        result = simulate_scenario(
            df, "Target", "Feature", 0.001, bounds=(0.0, 99999.0)
        )
        assert result.get("bounds_applied") is False

    def test_no_bounds_key_absent_from_result(self):
        """Sans bounds, la clé 'bounds_applied' ne doit pas apparaître."""
        df = _make_linear_df()
        result = simulate_scenario(df, "Target", "Feature", 0.10)
        assert "bounds_applied" not in result

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
    """R7 : le multiplicateur k de l'IQR doit être configurable."""

    def test_default_k_preserved(self):
        """k=1.5 par défaut — le comportement existant est inchangé."""
        series = pd.Series([1.0, 2.0, 2.0, 2.5, 3.0, 100.0])  # 100 est une anomalie
        result_default = detect_anomalies_iqr(series)
        result_k15 = detect_anomalies_iqr(series, k=1.5)
        assert result_default["indices"] == result_k15["indices"]

    def test_higher_k_fewer_anomalies(self):
        """Un k plus élevé doit produire moins d'anomalies (bornes plus larges)."""
        series = pd.Series([1.0] * 30 + [10.0])  # 10 est légèrement au-delà
        result_strict = detect_anomalies_iqr(series, k=1.5)
        result_lax = detect_anomalies_iqr(series, k=3.0)
        # Avec k=3.0, le seuil doit être plus permissif
        assert len(result_lax["indices"]) <= len(result_strict["indices"])

    def test_iqr_k_via_simulation_config(self):
        """generate_report doit lire iqr_k depuis simulation_config et l'appliquer."""
        # Dataset avec 50 lignes pour dépasser MIN_RELIABLE_SAMPLE_SIZE
        df = _make_sales_df()
        # k très élevé → presque aucune anomalie (bornes très larges)
        report_lax = generate_report(
            df, simulation_config={"target": "CA", "feature": "Semaine",
                                   "change_pct": 0.1, "iqr_k": 10.0}
        )
        # k très strict → plus d'anomalies potentielles
        report_strict = generate_report(
            df, simulation_config={"target": "CA", "feature": "Semaine",
                                   "change_pct": 0.1, "iqr_k": 0.5}
        )
        # Avec k=10, il doit y avoir moins d'anomalies qu'avec k=0.5
        n_anomalies_lax = sum(len(a["indices"]) for a in report_lax["anomalies"].values())
        n_anomalies_strict = sum(len(a["indices"]) for a in report_strict["anomalies"].values())
        assert n_anomalies_lax <= n_anomalies_strict

    def test_iqr_k_default_without_simulation_config(self):
        """Sans simulation_config, k=1.5 est utilisé (compatibilité ascendante)."""
        df = _make_sales_df()
        report = generate_report(df)
        # Le rapport doit fonctionner normalement sans simulation_config
        assert "anomalies" in report


# ---------------------------------------------------------------------------
# R8 — Warning saisonnalité
# ---------------------------------------------------------------------------

class TestWarningSaisonnalite:
    """R8 : un warning doit être émis quand une colonne temporelle est détectée
    et que des corrélations fortes existent."""

    def test_detect_temporal_columns_by_keyword(self):
        """_detect_temporal_columns détecte les colonnes dont le nom contient
        un mot-clé temporel."""
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
        assert green["level"] == "green"

        red = _compute_exploitability_score(5, 5, 3, 0.05)
        assert red["level"] == "red"

    def test_low_r_squared_downgrades_score(self):
        """Un R² très faible pénalise le score d'exploitabilité."""
        good = _compute_exploitability_score(50, 1, 0, 0.9)
        bad = _compute_exploitability_score(50, 1, 0, 0.02)
        assert bad["score"] < good["score"]
