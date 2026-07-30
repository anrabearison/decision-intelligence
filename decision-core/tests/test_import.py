"""
Tests du module d'import.
Périmètre Phase 1a : CSV et Excel, une seule table, première ligne = en-têtes.
"""
import os
import pytest
import pandas as pd
from decision_core.importer import import_file, UnsupportedFileFormatError

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture_path(name):
    return os.path.join(FIXTURES_DIR, name)


class TestImportCSV:
    def test_import_csv_returns_dataframe(self):
        df = import_file(fixture_path("ventes_test.csv"))
        assert isinstance(df, pd.DataFrame)

    def test_import_csv_correct_row_count(self):
        df = import_file(fixture_path("ventes_test.csv"))
        assert len(df) == 10

    def test_import_csv_correct_column_count(self):
        df = import_file(fixture_path("ventes_test.csv"))
        assert len(df.columns) == 7

    def test_import_csv_correct_column_names(self):
        df = import_file(fixture_path("ventes_test.csv"))
        expected = ["Date", "Produit", "Ville", "Prix", "Promotion", "Stock", "Ventes"]
        assert list(df.columns) == expected

    def test_import_csv_preserves_values(self):
        df = import_file(fixture_path("ventes_test.csv"))
        assert df.loc[0, "Produit"] == "Ordinateur"
        assert df.loc[0, "Prix"] == 850


class TestImportSemicolonSeparator:
    def test_import_detects_semicolon_separator(self, tmp_path):
        content = "a;b;c\n1;2;3\n4;5;6\n"
        f = tmp_path / "semicolon.csv"
        f.write_text(content)
        df = import_file(str(f))
        assert len(df.columns) == 3
        assert len(df) == 2


class TestImportExcel:
    def test_import_xlsx_returns_dataframe(self, tmp_path):
        df_source = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        f = tmp_path / "test.xlsx"
        df_source.to_excel(f, index=False)
        df = import_file(str(f))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["a", "b"]

    def test_import_xlsx_uses_first_sheet_only(self, tmp_path):
        f = tmp_path / "multi_sheet.xlsx"
        with pd.ExcelWriter(f) as writer:
            pd.DataFrame({"a": [1, 2]}).to_excel(writer, sheet_name="Feuille1", index=False)
            pd.DataFrame({"b": [3, 4, 5]}).to_excel(writer, sheet_name="Feuille2", index=False)
        df = import_file(str(f))
        assert "a" in df.columns
        assert len(df) == 2


class TestImportUnsupportedFormat:
    def test_import_rejects_unsupported_format(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}')
        with pytest.raises(UnsupportedFileFormatError):
            import_file(str(f))

    def test_import_rejects_missing_file(self):
        with pytest.raises(FileNotFoundError):
            import_file(fixture_path("does_not_exist.csv"))


class TestImportFrenchMissingValueConventions:
    def test_recognizes_nd_as_missing_value(self, tmp_path):
        # Trouvé en audit : "N/D" (Non Disponible, convention FR courante)
        # n'est pas dans la liste par défaut de pandas - une colonne
        # numérique à 80% devenait entièrement invisible de l'analyse.
        f = tmp_path / "prix_nd.csv"
        rows = ["Produit,Prix"]
        for i in range(30):
            prix = "N/D" if i % 5 == 0 else str(10 + i)
            rows.append(f"Produit_{i},{prix}")
        f.write_text("\n".join(rows))
        df = import_file(str(f))
        assert pd.api.types.is_numeric_dtype(df["Prix"])
        assert df["Prix"].isna().sum() == 6


class TestImportFrenchDecimalComma:
    def test_converts_decimal_comma_with_correct_delimiter(self, tmp_path):
        # Export Excel français correct (point-virgule + virgule décimale) :
        # doit être reconnu comme numérique, pas laissé en texte
        # (trouvé en audit : restait dtype str, classé à tort "datetime").
        f = tmp_path / "prix_fr.csv"
        rows = ["Produit;Prix"]
        for i in range(30):
            val = round(12.50 + i, 2)
            rows.append(f"Produit_{i};{str(val).replace('.', ',')}")
        f.write_text("\n".join(rows))
        df = import_file(str(f))
        assert pd.api.types.is_numeric_dtype(df["Prix"])
        assert df["Prix"].iloc[0] == pytest.approx(12.50, abs=0.01)

    def test_refuses_ambiguous_comma_delimited_decimal_comma_file(self, tmp_path):
        # Cas catastrophique trouvé en audit : virgule décimale FR dans un
        # fichier délimité par virgule (non échappé) produit une
        # corruption SILENCIEUSE des colonnes (décalage, données perdues).
        # Comportement attendu désormais : refuser plutôt que deviner.
        f = tmp_path / "prix_corrompu.csv"
        rows = ["Produit,Prix"]
        for i in range(30):
            val = round(12.50 + i, 2)
            rows.append(f"Produit_{i},{str(val).replace('.', ',')}")
        f.write_text("\n".join(rows))
        with pytest.raises(UnsupportedFileFormatError):
            import_file(str(f))

    def test_does_not_corrupt_row_count_when_refusing(self, tmp_path):
        # Non-régression explicite du bug de corruption : si jamais ce cas
        # est accepté par erreur dans le futur, au moins vérifier qu'il ne
        # produit jamais un DataFrame avec des colonnes décalées.
        f = tmp_path / "prix_corrompu2.csv"
        rows = ["Produit,Prix"]
        for i in range(30):
            val = round(12.50 + i, 2)
            rows.append(f"Produit_{i},{str(val).replace('.', ',')}")
        f.write_text("\n".join(rows))
        try:
            df = import_file(str(f))
            # si acceptée, la colonne Produit doit être présente et exploitable
            assert "Produit" in df.columns
            assert df["Produit"].iloc[0] == "Produit_0"
        except UnsupportedFileFormatError:
            pass  # comportement attendu et acceptable


class TestImportSingleColumnCsv:
    def test_imports_single_column_file_without_delimiter(self, tmp_path):
        # Régression trouvée en audit : le fix de cohérence de délimiteur
        # (P0) exigeait >= 2 champs dans l'en-tête pour tout délimiteur
        # candidat, rejetant à tort un fichier à une seule colonne (aucun
        # délimiteur n'est nécessaire ni présent dans ce cas légitime).
        f = tmp_path / "single_col.csv"
        f.write_text("Ventes\n100\n102\n98\n105\n")
        df = import_file(str(f))
        assert list(df.columns) == ["Ventes"]
        assert len(df) == 4


class TestImportEncodingFallback:
    def test_reads_windows_1252_encoded_file(self, tmp_path):
        # Export Excel Windows typique (très courant en contexte FR) :
        # encodage CP1252, pas UTF-8. Trouvé en audit : levait
        # UnicodeDecodeError brute (couverte en 400 côté API, mais le
        # fichier devrait pouvoir être lu correctement).
        f = tmp_path / "export_windows.csv"
        content = "Produit;Prix;Région\nÉcran;300;Antananarivo\nClavier;45;Fianarantsoa\n"
        f.write_bytes(content.encode("cp1252"))
        df = import_file(str(f))
        assert df.loc[0, "Produit"] == "Écran"
        assert df.loc[0, "Région"] == "Antananarivo"
