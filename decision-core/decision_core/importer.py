"""
Module d'import - Phase 1a.
Limites (voir README) : CSV et Excel uniquement, une seule table,
première feuille seulement pour Excel.

Ingestion locale-aware (voir README, section limites) : plusieurs bugs
réels ont été trouvés en audit sur des conventions françaises
d'export (Windows-1252, virgule décimale, "N/D" comme valeur
manquante). Traités ici comme un sous-système cohérent plutôt que des
patchs séparés, cf. commit.
"""
import csv
import os
import pandas as pd

# Encodages essayés dans l'ordre - UTF-8 d'abord (standard), CP1252
# (Windows-1252) en repli, très courant pour des exports Excel Windows
# en contexte francophone. Choix délibéré contre une détection
# automatique (chardet/charset-normalizer) : probabiliste, peu fiable
# sur petits fichiers, dépendance supplémentaire pour un gain marginal -
# ce repli déterministe couvre l'écrasante majorité des cas réels.
ENCODING_FALLBACKS = ["utf-8", "cp1252"]

# Conventions françaises de valeur manquante non couvertes par la liste
# par défaut de pandas (qui ne connaît que N/A, NA, NULL, none, nan...).
FRENCH_NA_VALUES = ["N/D", "ND", "N/C", "NC", "NR", "Non renseigné", "n.d.", "n.d"]

# Séparateur de milliers possible (espace normal ou insécable) à retirer
# avant de tenter une conversion numérique - convention française courante.
_THOUSANDS_SEPARATORS = ["\u202f", "\xa0", " "]


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


def _read_text_with_encoding_fallback(path: str) -> tuple[str, str]:
    last_error = None
    for encoding in ENCODING_FALLBACKS:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read(), encoding
        except UnicodeDecodeError as e:
            last_error = e
    raise UnsupportedFileFormatError(
        f"Impossible de déterminer l'encodage du fichier (essayé : "
        f"{', '.join(ENCODING_FALLBACKS)}) : {last_error}"
    )


def _detect_consistent_delimiter(text: str) -> str:
    """Choisit un délimiteur en vérifiant que le nombre de champs est
    cohérent sur un échantillon de lignes - évite la corruption
    silencieuse trouvée en audit (virgule décimale FR dans un fichier
    délimité par virgule, non échappé, produit un décalage de colonnes
    sans aucune erreur). Refuse plutôt que deviner si aucun délimiteur
    candidat n'est cohérent."""
    lines = [line for line in text.splitlines() if line.strip()][:20]
    if not lines:
        raise UnsupportedFileFormatError("Fichier vide ou sans contenu exploitable.")

    candidates = [",", ";", "\t"]
    try:
        sniffed = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
        candidates = [sniffed] + [c for c in candidates if c != sniffed]
    except csv.Error:
        pass

    # Fichier à une seule colonne : aucun délimiteur n'apparaît dans
    # l'en-tête, donc tous les candidats donnent 1 champ - c'est un cas
    # légitime (pas une incohérence), pas besoin de délimiteur du tout.
    # Trouvé en audit : la boucle ci-dessous rejetait ce cas à tort,
    # exigeant >= 2 champs pour TOUT candidat.
    if all(len(lines[0].split(d)) == 1 for d in candidates):
        return ","

    for delimiter in candidates:
        header_field_count = len(lines[0].split(delimiter))
        if header_field_count < 2:
            continue
        if all(len(line.split(delimiter)) == header_field_count for line in lines[1:]):
            return delimiter

    raise UnsupportedFileFormatError(
        "Impossible de déterminer un délimiteur cohérent pour ce fichier "
        "CSV - le nombre de champs varie selon les lignes. Cause "
        "fréquente : des valeurs décimales avec virgule (convention "
        "française) dans un fichier délimité par virgule. Utilisez un "
        "délimiteur point-virgule ou entourez les valeurs de guillemets."
    )


def _normalize_decimal_comma_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit les colonnes texte contenant des nombres au format
    français (virgule décimale, espace milliers) en colonnes numériques.
    Ne corrige jamais une ambiguïté réelle : seulement si >= 90% des
    valeurs non nulles deviennent des flottants valides après
    normalisation - une vraie colonne catégorielle/texte n'atteint
    jamais ce seuil par accident."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue

        cleaned = non_null.astype(str)
        for sep in _THOUSANDS_SEPARATORS:
            cleaned = cleaned.str.replace(sep, "", regex=False)
        cleaned = cleaned.str.replace(",", ".", regex=False)
        numeric = pd.to_numeric(cleaned, errors="coerce")

        if numeric.notna().mean() >= 0.9:
            full_cleaned = df[col].astype(str)
            for sep in _THOUSANDS_SEPARATORS:
                full_cleaned = full_cleaned.str.replace(sep, "", regex=False)
            full_cleaned = full_cleaned.str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(full_cleaned, errors="coerce")

    return df


def _import_csv(path: str) -> pd.DataFrame:
    text, encoding = _read_text_with_encoding_fallback(path)
    sep = _detect_consistent_delimiter(text)
    df = pd.read_csv(
        path, sep=sep, encoding=encoding,
        na_values=FRENCH_NA_VALUES, keep_default_na=True,
    )
    return _normalize_decimal_comma_columns(df)


def _import_excel(path: str) -> pd.DataFrame:
    # Phase 1a : première feuille uniquement (limite documentée dans le README)
    return pd.read_excel(path, sheet_name=0, na_values=FRENCH_NA_VALUES, keep_default_na=True)
