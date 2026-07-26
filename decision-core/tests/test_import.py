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
