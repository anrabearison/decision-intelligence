"""
Tests de détection automatique des types de colonnes.
Heuristique documentée dans le README (limite connue : imparfaite).
"""
import os
import pandas as pd
from decision_core.type_detection import detect_column_type

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    return pd.read_csv(os.path.join(FIXTURES_DIR, name))


class TestTypeDetectionVentes:
    def setup_method(self):
        self.df = load("ventes_test.csv")

    def test_prix_is_numeric(self):
        # Cas limite documenté (README) : Prix ne contient que des valeurs
        # entières dans ce jeu de données -> l'heuristique le classe en
        # "numeric_discrete", bien qu'un prix soit conceptuellement continu.
        # On teste ici le comportement réel de l'heuristique, pas une
        # interprétation métier qu'elle n'est pas censée avoir en Phase 1a.
        assert detect_column_type(self.df["Prix"]) in ("numeric_discrete", "numeric_continuous")

    def test_ventes_is_numeric_discrete(self):
        assert detect_column_type(self.df["Ventes"]) == "numeric_discrete"

    def test_produit_is_categorical(self):
        assert detect_column_type(self.df["Produit"]) == "categorical"

    def test_ville_is_categorical(self):
        assert detect_column_type(self.df["Ville"]) == "categorical"

    def test_promotion_is_boolean(self):
        assert detect_column_type(self.df["Promotion"]) == "boolean"


class TestTypeDetectionTroupeau:
    def setup_method(self):
        self.df = load("troupeau_test.csv")

    def test_animal_is_identifier(self):
        # quasi 100% de valeurs uniques -> identifiant
        assert detect_column_type(self.df["Animal"]) == "identifier"

    def test_race_is_categorical(self):
        assert detect_column_type(self.df["Race"]) == "categorical"

    def test_temperature_is_numeric_continuous(self):
        assert detect_column_type(self.df["Temperature"]) == "numeric_continuous"

    def test_vaccin_is_boolean(self):
        assert detect_column_type(self.df["Vaccin"]) == "boolean"


class TestTypeDetectionEdgeCases:
    def test_o_n_french_abbreviation_is_boolean(self):
        # Abréviation française très courante (Oui/Non) - trouvée en
        # audit, absente de la liste initiale de paires booléennes.
        s = pd.Series(["O", "N", "O", "O", "N", "O", "N", "O", "O", "N"])
        assert detect_column_type(s) == "boolean"

    def test_all_unique_strings_is_identifier_or_text(self):
        s = pd.Series(["a1", "b2", "c3", "d4", "e5"])
        assert detect_column_type(s) in ("identifier", "text_free")

    def test_pure_numeric_series(self):
        s = pd.Series([1.1, 2.2, 3.3, 4.4])
        assert detect_column_type(s) == "numeric_continuous"

    def test_two_unique_values_is_boolean(self):
        s = pd.Series(["Oui", "Non", "Oui", "Oui", "Non"])
        assert detect_column_type(s) == "boolean"
