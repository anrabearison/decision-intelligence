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
from decision_core.reporting.warnings import _build_asymmetry_warnings
from decision_core.models import SimulationConfig

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

    def test_significant_subgroups_do_not_depend_on_numeric_column_order(self):
        df = pd.DataFrame({
            "target": [10, 10, 20, 20, 30, 30],
            "other": [1, 2, 1, 2, 1, 2],
            "cat": ["A", "A", "B", "B", "C", "C"],
        })
        reordered = df[["other", "target", "cat"]]

        report_original = generate_report(df)
        report_reordered = generate_report(reordered)

        subgroup_warnings_original = [
            w for w in report_original["warnings"]
            if "Sous-groupe significatif détecté" in w
        ]
        subgroup_warnings_reordered = [
            w for w in report_reordered["warnings"]
            if "Sous-groupe significatif détecté" in w
        ]

        assert subgroup_warnings_original == subgroup_warnings_reordered

    def test_profiling_excludes_identifier_columns(self):
        # Cohérence avec correlation_matrix (déjà corrigé) : une colonne
        # identifiant (numéro de lot séquentiel) n'a pas de moyenne/écart-type
        # statistiquement significatifs - trouvé en revue de code, le fix
        # précédent n'avait été appliqué qu'à correlation_matrix, pas au
        # profiling qui utilisait une liste de colonnes numériques séparée.
        df = pd.DataFrame({
            "Numero_lot": range(1, 31),
            "Temperature": [70, 71, 70, 72, 71, 70, 73, 71, 70, 72] * 3,
        })
        report = generate_report(df)
        assert "Numero_lot" not in report["profiling"]
        assert "Temperature" in report["profiling"]

    def test_warns_explicitly_when_no_numeric_column_exists(self):
        # Trouvé en audit : un dataset entièrement catégoriel produisait
        # un rapport vide (profiling: {}, top_correlations: [], anomalies:
        # {}) sans jamais expliquer pourquoi - indiscernable pour
        # l'utilisateur d'un cas où l'analyse a simplement ne rien trouvé
        # d'intéressant sur de vraies colonnes numériques.
        df = pd.DataFrame({
            "Produit": ["Chaise", "Table", "Lampe"] * 10,
            "Ville": ["Paris", "Lyon", "Marseille"] * 10,
        })
        report = generate_report(df)
        assert any(
            "aucune colonne numérique" in w.lower() for w in report["warnings"]
        )

    def test_no_such_warning_when_numeric_columns_exist(self):
        df = load("ventes_test.csv")
        report = generate_report(df)
        assert not any(
            "aucune colonne numérique" in w.lower() for w in report["warnings"]
        )


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


class TestReportIncludesAnomalyDetection:
    def test_report_flags_obvious_anomaly(self):
        # Cas trouvé en audit : detect_anomalies_iqr existait, testé,
        # mais jamais appelé dans generate_report - une anomalie
        # évidente (5000 parmi des valeurs ~100) passait totalement
        # inaperçue, alors que le texte du rapport prétendait déjà que
        # la détection d'anomalies faisait partie de l'analyse.
        df = pd.DataFrame({
            "Ventes": [100, 102, 98, 105, 99, 101, 103, 97, 100, 102,
                       101, 99, 103, 100, 98, 102, 101, 5000, 99, 100,
                       103, 101, 98, 100, 102, 99, 101, 100, 103, 98],
        })
        report = generate_report(df)
        assert "anomalies" in report
        assert "Ventes" in report["anomalies"]
        assert 17 in report["anomalies"]["Ventes"]["indices"]

    def test_no_anomalies_key_for_column_without_anomalies(self):
        df = pd.DataFrame({"Valeurs": [10, 11, 9, 10, 12, 9, 11, 10, 9, 11] * 3})
        report = generate_report(df)
        assert "Valeurs" not in report.get("anomalies", {})

    def test_warns_when_anomalies_detected(self):
        df = pd.DataFrame({
            "Ventes": [100, 102, 98, 105, 99, 101, 103, 97, 100, 102,
                       101, 99, 103, 100, 98, 102, 101, 5000, 99, 100,
                       103, 101, 98, 100, 102, 99, 101, 100, 103, 98],
        })
        report = generate_report(df)
        assert any("anomalie" in w.lower() for w in report["warnings"])

    def test_no_anomaly_warning_when_sample_too_small_to_be_reliable(self):
        # Sous le seuil MIN_RELIABLE_SAMPLE_SIZE (30), detect_anomalies_iqr
        # marque reliable=False - ne doit jamais produire d'avertissement
        # "anomalie détectée" trompeur sur un échantillon non fiable.
        df = pd.DataFrame({"Valeurs": [10, 11, 9, 10, 12, 9, 11, 10, 500]})
        report = generate_report(df)
        assert not any("anomalie" in w.lower() and "détectée" in w.lower() for w in report["warnings"])


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

    def test_influential_point_warning_never_makes_a_false_claim_about_iqr(self):
        # Trouvé en audit : le message affirmait "même s'il n'est pas
        # détecté comme anomalie sur une seule colonne" - affirmation
        # fausse dans ce cas précis, où le point influent EST aussi
        # détecté par IQR sur les deux colonnes. Le message ne doit
        # jamais faire d'affirmation dont la véracité dépend du rapport.
        np.random.seed(3)
        prix = list(np.random.uniform(20, 30, 29)) + [9999]
        ventes = list(100 - 2 * np.array(prix[:29]) + np.random.normal(0, 3, 29)) + [5]
        df = pd.DataFrame({"Prix": prix, "Ventes": ventes})
        report = generate_report(df, simulation_config={"target": "Ventes", "feature": "Prix", "change_pct": 0.1})
        influence_warning = next(w for w in report["warnings"] if "influent" in w.lower())
        assert "même s'il n'est pas détecté" not in influence_warning

    def test_warns_when_effective_simulation_sample_is_small_despite_large_dataset(self):
        # Dataset global de 40 lignes (au-dessus du seuil "petit
        # échantillon" global), mais seulement 5 valeurs valides sur les
        # colonnes utilisées par la simulation après retrait des NaN -
        # doit être signalé même si n_rows global ne l'est pas.
        np.random.seed(1)
        n = 40
        df = pd.DataFrame({
            "Autre_colonne": np.random.normal(50, 5, n),
            "X": [1, 2, 3, 4, 5] + [None] * 35,
            "Y": [10, 22, 28, 41, 48] + [None] * 35,
        })
        report = generate_report(df, simulation_config={"target": "Y", "feature": "X", "change_pct": 0.1})
        assert report["dataset_summary"]["n_rows"] == 40  # dataset global bien à 40
        assert any(
            "5" in w and ("échantillon" in w.lower() or "valides" in w.lower())
            for w in report["warnings"]
        )

    def test_warns_when_correlation_columns_are_capped(self):
        # Trouvé en audit de performance : au-delà de
        # MAX_COLUMNS_FOR_CORRELATION colonnes, seules les N premières
        # sont utilisées pour les corrélations - doit être signalé
        # explicitement, pas silencieux.
        rng = np.random.default_rng(0)
        df = pd.DataFrame({f"V{i}": rng.normal(0, 1, 30) for i in range(80)})
        report = generate_report(df)
        assert any("50" in w and "colonnes" in w.lower() for w in report["warnings"])

    def test_excludes_derived_column_relationship_from_top_correlations(self):
        # Trouvé en test de lisibilité simulé : Total = Prix * Quantité
        # apparaissait comme "la corrélation la plus forte" - une
        # tautologie arithmétique, pas un insight. Ne doit plus jamais
        # être présenté comme tel.
        rng = np.random.default_rng(0)
        n = 40
        prix = rng.uniform(10, 100, n)
        quantite = rng.integers(1, 20, n).astype(float)
        total = prix * quantite
        autre = rng.normal(0, 1, n)  # variable non liée, pour vérifier qu'elle reste éligible
        df = pd.DataFrame({"Prix": prix, "Quantite": quantite, "Total": total, "Autre": autre})
        report = generate_report(df)
        pairs = {frozenset([c["column_a"], c["column_b"]]) for c in report["top_correlations"]}
        assert frozenset(["Prix", "Total"]) not in pairs
        assert frozenset(["Quantite", "Total"]) not in pairs

    def test_warns_about_derived_column_relationship(self):
        rng = np.random.default_rng(0)
        n = 40
        prix = rng.uniform(10, 100, n)
        quantite = rng.integers(1, 20, n).astype(float)
        total = prix * quantite
        df = pd.DataFrame({"Prix": prix, "Quantite": quantite, "Total": total})
        report = generate_report(df)
        assert any("calculée" in w.lower() or "dérivée" in w.lower() for w in report["warnings"])


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

    def test_text_summary_uses_percentage_points_for_binary_target(self):
        df = pd.DataFrame({
            "Tickets_Support": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "Desabonnement_Churn": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1],
        })
        report = generate_report(
            df,
            simulation_config={
                "target": "Desabonnement_Churn",
                "feature": "Tickets_Support",
                "change_pct": 0.5,
            },
        )
        text = render_text_summary(report)
        assert "points" in text
        assert "+1009" not in text


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

    def test_html_escapes_column_names_to_prevent_injection(self):
        # Un nom de colonne vient de données non fiables (en-tête CSV
        # uploadé par l'utilisateur) - ne doit jamais être injecté tel
        # quel dans le HTML produit (risque XSS).
        df = pd.DataFrame({
            "<script>alert(1)</script>": [1, 2, 3, 4, 5] * 8,
            "B": [5, 4, 3, 2, 1] * 8,
        })
        report = generate_report(df)
        html = render_html(report)
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html


class TestAsymmetryWarnings:
    """Tests pour la détection d'asymétrie (F3 - Baseline peu représentative)."""

    def test_detects_asymmetric_distribution(self):
        """Teste la détection d'une distribution asymétrique (Pareto)."""
        df = pd.DataFrame({
            "Cost": [15000, 12000, 18000, 10000, 20000, 950000, 280000, 320000, 15000, 12000]
        })
        warnings = []
        _build_asymmetry_warnings(df, ["Cost"], [], warnings)
        assert len(warnings) == 1
        assert "Distribution asymétrique détectée pour 'Cost'" in warnings[0]
        assert "Cost" in warnings[0]
        assert "165 200" in warnings[0]  # moyenne calculée

    def test_no_warning_on_symmetric_distribution(self):
        """Teste qu'une distribution symétrique ne génère pas de warning."""
        np.random.seed(42)
        df = pd.DataFrame({
            "Normal": np.random.normal(100, 10, 20)
        })
        warnings = []
        _build_asymmetry_warnings(df, ["Normal"], [], warnings)
        assert len(warnings) == 0

    def test_suggests_segmentation_when_subgroup_detected(self):
        """Teste la suggestion de segmentation quand un sous-groupe existe."""
        df = pd.DataFrame({
            "Cost": [15000, 12000, 18000, 10000, 20000, 950000, 280000, 320000, 15000, 12000]
        })
        warnings = []
        _build_asymmetry_warnings(df, ["Cost"], ["Severity"], warnings)
        assert len(warnings) == 2
        assert any("Distribution asymétrique détectée pour 'Cost'" in w for w in warnings)
        assert any("segmente fortement les données" in w for w in warnings)

    def test_handles_zero_std_gracefully(self):
        """Teste le cas où std = 0 (toutes les valeurs identiques)."""
        df = pd.DataFrame({
            "Constant": [100] * 10
        })
        warnings = []
        _build_asymmetry_warnings(df, ["Constant"], [], warnings)
        assert len(warnings) == 0  # Pas de division par zéro

    def test_integration_with_generate_report(self):
        """Teste l'intégration dans generate_report."""
        df = pd.DataFrame({
            "Cost": [15000, 12000, 18000, 10000, 20000, 950000, 280000, 320000, 15000, 12000]
        })
        report = generate_report(df)
        asymmetry_warnings = [w for w in report.warnings if "Distribution asymétrique" in w]
        assert len(asymmetry_warnings) == 1

    def test_simulation_context_limits_warning_to_target_and_feature(self):
        """Avec simulation, seuls target/feature peuvent produire une alerte contextuelle."""
        df = pd.DataFrame({
            "Cost": [15000, 12000, 18000, 10000, 20000, 950000, 280000, 320000, 15000, 12000],
            "Systems": [1, 1, 2, 1, 2, 20, 12, 14, 1, 1],
            "OtherSkewed": [2, 2, 2, 2, 2, 500, 600, 700, 2, 2],
        })
        warnings = []
        config = SimulationConfig(target="Cost", feature="Systems", change_pct=0.2)
        _build_asymmetry_warnings(
            df,
            ["Cost", "Systems", "OtherSkewed"],
            [],
            warnings,
            simulation_config=config,
        )
        assert warnings
        assert any("Baseline de simulation peu représentative pour la cible 'Cost'" in w for w in warnings)
        assert any("Point de départ du scénario peu représentatif pour le levier 'Systems'" in w for w in warnings)
        assert not any("OtherSkewed" in w for w in warnings)

    def test_without_simulation_limits_general_asymmetry_warnings_to_top_three(self):
        """Sans simulation, le warning général reste limité pour éviter le bruit."""
        df = pd.DataFrame({
            f"Skewed_{i}": [1, 1, 1, 1, 1, 100 * (i + 1), 120 * (i + 1), 140 * (i + 1), 1, 1]
            for i in range(5)
        })
        warnings = []
        _build_asymmetry_warnings(df, list(df.columns), [], warnings)
        assert len(warnings) == 3
        assert all("Distribution asymétrique détectée" in w for w in warnings)


class TestDistributionWarnings:
    def test_detects_count_data_warning(self):
        df = pd.DataFrame({
            "Anomalies_Comptees": [1, 2, 1, 2, 3, 2, 1, 2, 3, 4, 5, 2, 1, 2, 3]
        })
        report = generate_report(df)
        assert any("Distribution de comptage détectée" in w for w in report["warnings"])
        assert not any("Distribution zéro-inflated détectée" in w for w in report["warnings"])

    def test_detects_zero_inflated_warning(self):
        df = pd.DataFrame({"Cout_Indemnisation_Euros": [0, 0, 0, 100, 0, 0, 200, 0, 0, 300]})
        report = generate_report(df)
        assert any("Distribution zéro-inflated détectée" in w for w in report["warnings"])

    def test_detects_heavy_tail_warning(self):
        df = pd.DataFrame({"Cout_Incident_Euros": [1, 2, 2, 3, 5, 10, 20, 100, 500, 2000]})
        report = generate_report(df)
        assert any("Distribution à queue lourde détectée" in w for w in report["warnings"])

    def test_combines_count_and_zero_inflated_warnings_into_one(self):
        df = pd.DataFrame({
            "Nombre_Sinistres": [0, 0, 1, 0, 2, 0, 3, 0, 0, 4, 0, 0, 1, 0, 2]
        })
        report = generate_report(df)
        combined_warnings = [
            w for w in report["warnings"]
            if "Distribution de comptage avec forte proportion de zéros détectée" in w
        ]
        assert len(combined_warnings) == 1
        assert not any(
            "Distribution de comptage détectée" in w and "forte proportion de zéros" not in w
            for w in report["warnings"]
        )
        assert not any(
            "Distribution zéro-inflated détectée" in w and "forte proportion de zéros" not in w
            for w in report["warnings"]
        )

    def test_count_zero_columns_are_excluded_from_asymmetry_warnings(self):
        df = pd.DataFrame({
            "Nombre_Sinistres": [0, 0, 1, 0, 2, 0, 3, 0, 0, 4, 0, 0, 1, 0, 2,
                                   0, 1, 2, 0, 0, 1, 3, 0, 0, 2, 0, 0, 1, 0, 3],
            "Revenu": [100] * 20 + [1000] * 10,
        })
        report = generate_report(df)
        assert any("Distribution de comptage avec forte proportion de zéros détectée" in w for w in report["warnings"])
        assert not any("Distribution asymétrique détectée pour 'Nombre_Sinistres'" in w for w in report["warnings"])
        assert any("Distribution asymétrique détectée" in w for w in report["warnings"])
