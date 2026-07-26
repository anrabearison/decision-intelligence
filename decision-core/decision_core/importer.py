"""
Module d'import - Phase 1a.
Limites (voir README) : CSV et Excel uniquement, une seule table,
première feuille seulement pour Excel.
"""
import os
import csv
import pandas as pd


class UnsupportedFileFormatError(Exception):
    pass


def import_file(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier introuvable : {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".csv":
        return _import_csv(path)
    elif ext in (".xlsx", ".xls"):
        return _import_excel(path)
    else:
        raise UnsupportedFileFormatError(
            f"Format non supporté : {ext}. Phase 1a n'accepte que CSV et Excel."
        )


def _import_csv(path: str) -> pd.DataFrame:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        sample = f.read(4096)
    try:
        sep = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        sep = ","
    return pd.read_csv(path, sep=sep)


def _import_excel(path: str) -> pd.DataFrame:
    # Phase 1a : première feuille uniquement (limite documentée dans le README)
    return pd.read_excel(path, sheet_name=0)
