"""
Tests du module de rapport - Phase 1a.
Rôle : assembler validation + profiling + simulation en une synthèse
lisible (dict structuré + rendu texte + rendu HTML).
Le rapport ne doit jamais présenter comme "insight principal" une
corrélation triviale (cf. remarque utilisateur / README).
"""
import os
import numpy as np
import pandas as pd
import pytest
from decision_core.report import generate_report, render_text_summary, render_html

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    return pd.read_csv(os.path.join(FIXTURES_DIR, name))


class TestGenerateReportStructure:
    def test_report_has_required_sections(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        assert "dataset_summary" in report
        assert "validation" in report
        assert "profiling" in report
        assert "top_correlations" in report
        assert "warnings" in report

    def test_dataset_summary_counts(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        assert report["dataset_summary"]["n_rows"] == 10
        assert report["dataset_summary"]["n_columns"] == 7


class TestReportSmallSampleWarning:
    def test_warns_on_small_sample(self):
        df = load("ventes_test.csv")  # 10 lignes < 30
        report = generate_report(df)
        assert any("échantillon" in w.lower() for w in report["warnings"])

    def test_no_small_sample_warning_above_threshold(self):
        df = pd.DataFrame({"a": range(50), "b": range(50, 100)})
        report = generate_report(df)
        assert not any("échantillon" in w.lower() for w in report["warnings"])


class TestReportTopCorrelations:
    def test_top_correlations_sorted_by_strength(self):
        df = load("tresorerie_test.csv")
        report = generate_report(df)
        correlations = report["top_correlations"]
        # triées par valeur absolue décroissante
        abs_values = [abs(c["value"]) for c in correlations]
        assert abs_values == sorted(abs_values, reverse=True)

    def test_top_correlations_exclude_self_pairs(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        for c in report["top_correlations"]:
            assert c["column_a"] != c["column_b"]

    def test_top_correlations_no_duplicate_pairs(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        seen = set()
        for c in report["top_correlations"]:
            pair = frozenset([c["column_a"], c["column_b"]])
            assert pair not in seen
            seen.add(pair)


class TestReportWithSimulation:
    def test_report_includes_simulation_when_provided(self):
        df = load("ventes_test.csv")
        report = generate_report(
            df,
            simulation_config={"target": "Ventes", "feature": "Prix", "change_pct": 0.05},
        )
        assert "simulation" in report
        assert report["simulation"]["feature"] == "Prix"
        assert report["simulation"]["simulated"] < report["simulation"]["baseline"]

    def test_report_without_simulation_config_has_no_simulation_key(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        assert "simulation" not in report

    def test_warns_when_simulation_r_squared_is_low(self):
        df = pd.DataFrame({
            "X": list(range(1, 41)),
            "Y": [50, 51, 49, 52, 48, 50, 51, 49, 53, 47,
                  50, 52, 48, 51, 49, 50, 53, 47, 51, 49,
                  50, 51, 49, 52, 48, 50, 51, 49, 53, 47,
                  50, 52, 48, 51, 49, 50, 53, 47, 51, 49],
        })
        report = generate_report(df, simulation_config={"target": "Y", "feature": "X", "change_pct": 0.1})
        assert any("r²" in w.lower() or "r2" in w.lower() for w in report["warnings"])

    def test_warns_when_simulation_relies_on_influential_point(self):
        # point individuellement plausible mais bivariablement incohérent -
        # cf. test_influence_detection.py, IQR seul ne le détecte pas.
        np.random.seed(11)
        n = 29
        X = np.random.uniform(10, 30, n)
        Y = 2 * X + np.random.normal(0, 3, n)
        X = np.append(X, 15)
        Y = np.append(Y, 55)
        df = pd.DataFrame({"X": X, "Y": Y})
        report = generate_report(df, simulation_config={"target": "Y", "feature": "X", "change_pct": 0.1})
        assert any("influent" in w.lower() for w in report["warnings"])


class TestRenderTextSummary:
    def test_text_summary_is_string(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        text = render_text_summary(report)
        assert isinstance(text, str)
        assert len(text) > 0

    def test_text_summary_mentions_row_count(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        text = render_text_summary(report)
        assert "10" in text

    def test_text_summary_includes_causality_disclaimer_when_correlation_shown(self):
        df = load("troupeau_test.csv")
        report = generate_report(df)
        text = render_text_summary(report)
        assert "causalité" in text.lower()

    def test_text_summary_does_not_crash_when_change_pct_unreliable(self):
        df = pd.DataFrame({
            "X": list(range(1, 21)),
            "Y": [9.45, 2.68, 0.98, -8.82, -0.88, -1.27, 0.09, -2.63, 0.28, -1.88,
                  -6.07, 4.93, 4.91, 9.05, 0.75, -1.52, -2.22, -7.23, 5.41, -5.0],
        })
        report = generate_report(df, simulation_config={"target": "Y", "feature": "X", "change_pct": 0.1})
        text = render_text_summary(report)  # ne doit pas lever d'exception
        assert "non fiable" in text.lower() or "peu fiable" in text.lower()


class TestRenderHtml:
    def test_html_is_valid_looking_string(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        html = render_html(report)
        assert "<html" in html.lower()
        assert "</html>" in html.lower()

    def test_html_contains_dataset_row_count(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        html = render_html(report)
        assert "10" in html
