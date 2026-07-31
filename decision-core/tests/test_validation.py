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

    def test_detects_duplicates_with_non_english_identifier_column_name(self):
        # Trouvé en audit : l'exclusion précédente ne reconnaissait que
        # la colonne nommée exactement "id" - un identifiant nommé
        # "Identifiant" (français, très courant) n'était jamais exclu,
        # faisant passer inaperçus de vrais doublons métier.
        df = pd.DataFrame({
            "Identifiant": [1, 2, 3, 4, 5],
            "Produit": ["Chaise", "Chaise", "Table", "Table", "Lampe"],
            "Prix": [50, 60, 100, 100, 30],
        })
        result = validate_dataset(df)
        assert result["duplicates_count"] == 1

    def test_does_not_crash_when_every_column_looks_like_an_identifier(self):
        # Cas limite trouvé en écrivant le fix ci-dessus : si toutes les
        # colonnes ressemblent à un identifiant (ex: deux séquences 1..n),
        # exclure tout laisserait un subset vide - df.duplicated(subset=[])
        # plante avec une erreur pandas interne sans ce garde-fou.
        df = pd.DataFrame({"a": range(50), "b": range(50, 100)})
        result = validate_dataset(df)
        assert result["duplicates_count"] == 0
