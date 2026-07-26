"""
Tests du module de validation.
Rôle : signaler les problèmes (doublons, valeurs manquantes) -
ne les corrige jamais automatiquement en Phase 1a (cf. README, Limites).
"""
import os
import pandas as pd
from decision_core.validation import validate_dataset

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    return pd.read_csv(os.path.join(FIXTURES_DIR, name))


class TestValidationCleanDataset:
    def test_clean_dataset_no_duplicates(self):
        df = load("ventes_test.csv")
        result = validate_dataset(df)
        assert result["duplicates_count"] == 0

    def test_clean_dataset_no_missing_values(self):
        df = load("ventes_test.csv")
        result = validate_dataset(df)
        assert all(v == 0 for v in result["missing_values"].values())

    def test_row_and_column_counts(self):
        df = load("ventes_test.csv")
        result = validate_dataset(df)
        assert result["n_rows"] == 10
        assert result["n_columns"] == 7


class TestValidationProblematicDataset:
    def test_detects_duplicates(self):
        df = load("dataset_avec_problemes.csv")
        result = validate_dataset(df)
        # la ligne id=3 est un doublon exact de id=1 (hors colonne id elle-même
        # si on compare content-wise ; ici on compare sur les colonnes hors id)
        assert result["duplicates_count"] >= 1

    def test_detects_missing_values_per_column(self):
        df = load("dataset_avec_problemes.csv")
        result = validate_dataset(df)
        assert result["missing_values"]["quantite"] == 1
        assert result["missing_values"]["ville"] == 1

    def test_validation_does_not_mutate_original_dataframe(self):
        df = load("dataset_avec_problemes.csv")
        n_rows_before = len(df)
        validate_dataset(df)
        assert len(df) == n_rows_before  # aucune correction/suppression automatique
