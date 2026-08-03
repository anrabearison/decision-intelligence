"""
Tests du module de traitement des variables catégorielles.
"""
import pandas as pd
import numpy as np
import pytest
from decision_core.stats.categorical import (
    encode_categorical_features,
    detect_significant_subgroups,
    generate_segmented_reports,
)


class TestEncodeCategoricalFeatures:
    def test_encodes_string_columns_with_low_cardinality(self):
        """Test que les colonnes texte avec peu de valeurs sont encodées en one-hot."""
        df = pd.DataFrame({
            "A": [1, 2, 3, 4],
            "B": ["X", "Y", "X", "Y"],
            "C": ["P", "P", "P", "Q"],
        })
        encoded = encode_categorical_features(df, max_cardinality=10)
        
        # Vérifier que les colonnes originales sont supprimées
        assert "B" not in encoded.columns
        assert "C" not in encoded.columns
        
        # Vérifier que les colonnes one-hot sont créées
        assert "B_Y" in encoded.columns
        assert "C_Q" in encoded.columns
        
        # Vérifier que les colonnes numériques sont préservées
        assert "A" in encoded.columns

    def test_does_not_encode_high_cardinality_columns(self):
        """Test que les colonnes avec beaucoup de valeurs ne sont pas encodées."""
        df = pd.DataFrame({
            "A": list(range(15)),
            "B": [f"cat_{i}" for i in range(15)],  # 15 valeurs uniques
        })
        encoded = encode_categorical_features(df, max_cardinality=10)
        
        # La colonne B ne doit pas être encodée (cardinalité > 10)
        assert "B" in encoded.columns
        assert not any(col.startswith("B_") for col in encoded.columns)

    def test_preserves_numeric_columns(self):
        """Test que les colonnes numériques sont préservées."""
        df = pd.DataFrame({
            "A": [1, 2, 3, 4],
            "B": [1.5, 2.5, 3.5, 4.5],
        })
        encoded = encode_categorical_features(df)
        
        assert "A" in encoded.columns
        assert "B" in encoded.columns
        assert encoded["A"].dtype == df["A"].dtype


class TestDetectSignificantSubgroups:
    def test_detects_subgroups_with_high_eta_squared(self):
        """Test que les sous-groupes avec eta-carré élevé sont détectés."""
        df = pd.DataFrame({
            "target": [10, 12, 20, 22, 30, 32],
            "group": ["A", "A", "B", "B", "C", "C"],
        })
        # Les groupes A, B, C ont des moyennes distinctes (11, 21, 31)
        subgroups = detect_significant_subgroups(df, "target", threshold_eta_squared=0.5)
        
        assert len(subgroups) == 1
        assert subgroups[0]["column"] == "group"
        assert subgroups[0]["eta_squared"] > 0.5

    def test_does_not_detect_weak_subgroups(self):
        """Test que les sous-groupes avec eta-carré faible ne sont pas détectés."""
        # Données avec beaucoup de bruit et peu de différence entre groupes
        np.random.seed(42)
        df = pd.DataFrame({
            "target": [10 + np.random.randn() * 5 for _ in range(4)] + 
                      [11 + np.random.randn() * 5 for _ in range(4)] + 
                      [12 + np.random.randn() * 5 for _ in range(4)],
            "group": ["A"] * 4 + ["B"] * 4 + ["C"] * 4,
        })
        # Les groupes ont des moyennes très proches (~10, ~11, ~12) avec beaucoup de variance intra-groupe
        subgroups = detect_significant_subgroups(df, "target", threshold_eta_squared=0.5)
        
        # Avec un seuil de 0.5 (très grand effet), aucun sous-groupe ne doit être détecté
        assert len(subgroups) == 0

    def test_returns_empty_for_non_numeric_target(self):
        """Test que rien n'est retourné pour une cible non numérique."""
        df = pd.DataFrame({
            "target": ["A", "B", "C", "D"],
            "group": ["X", "X", "Y", "Y"],
        })
        subgroups = detect_significant_subgroups(df, "target")
        
        assert len(subgroups) == 0

    def test_includes_group_means_in_result(self):
        """Test que les moyennes par groupe sont incluses dans le résultat."""
        df = pd.DataFrame({
            "target": [10, 12, 20, 22],
            "group": ["A", "A", "B", "B"],
        })
        subgroups = detect_significant_subgroups(df, "target", threshold_eta_squared=0.1)
        
        assert len(subgroups) == 1
        assert "group_means" in subgroups[0]
        assert abs(subgroups[0]["group_means"]["A"] - 11.0) < 0.1
        assert abs(subgroups[0]["group_means"]["B"] - 21.0) < 0.1


class TestGenerateSegmentedReports:
    def test_generates_reports_for_each_subgroup(self):
        """Test que des rapports sont générés pour chaque sous-groupe."""
        df = pd.DataFrame({
            "A": [1, 2, 3, 4, 5, 6],
            "B": [2, 4, 6, 8, 10, 12],
            "group": ["X", "X", "X", "Y", "Y", "Y"],
        })
        
        def mock_generate_report(df, config):
            return {"n_rows": len(df)}
        
        reports = generate_segmented_reports(
            df, 
            group_by=["group"], 
            generate_report_func=mock_generate_report, 
            config=None
        )
        
        assert len(reports) == 2
        assert "X" in reports
        assert "Y" in reports
        assert reports["X"]["n_rows"] == 3
        assert reports["Y"]["n_rows"] == 3

    def test_skips_small_groups(self):
        """Test que les groupes trop petits sont ignorés."""
        df = pd.DataFrame({
            "A": [1, 2, 3],
            "B": [2, 4, 6],
            "group": ["X", "X", "Y"],
        })
        
        def mock_generate_report(df, config):
            return {"n_rows": len(df)}
        
        reports = generate_segmented_reports(
            df, 
            group_by=["group"], 
            generate_report_func=mock_generate_report, 
            config=None,
            min_group_size=3
        )
        
        # Seul le groupe X (2 lignes) devrait être ignoré
        assert len(reports) == 0

    def test_handles_multiple_grouping_columns(self):
        """Test le groupement par plusieurs colonnes."""
        df = pd.DataFrame({
            "A": [1, 2, 3, 4, 5, 6, 7, 8],
            "B": [2, 4, 6, 8, 10, 12, 14, 16],
            "group1": ["X", "X", "X", "X", "Y", "Y", "Y", "Y"],
            "group2": ["A", "A", "B", "B", "A", "A", "B", "B"],
        })
        
        def mock_generate_report(df, config):
            return {"n_rows": len(df)}
        
        reports = generate_segmented_reports(
            df, 
            group_by=["group1", "group2"], 
            generate_report_func=mock_generate_report, 
            config=None,
            min_group_size=2
        )
        
        # 4 combinaisons possibles avec 2 lignes chacune
        assert len(reports) == 4
