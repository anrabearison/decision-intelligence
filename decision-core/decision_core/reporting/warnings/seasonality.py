"""
Warnings de saisonnalité pour decision-core (R8).
"""
import re
import pandas as pd
from .constants import _TEMPORAL_KEYWORDS

__all__ = ["_detect_temporal_columns", "_build_seasonality_warnings"]


def _detect_temporal_columns(df: pd.DataFrame) -> list:
    """Retourne la liste des noms de colonnes dont le nom suggère une
    dimension temporelle (date, semaine, saison, etc.).

    La détection se fait par découpage du nom en mots (éparateurs _ - espace
    et split CamelCase) pour éviter les faux positifs sur des mots composés
    contenant un mot-clé temporel en sous-chaîne :
      - 'Bonjour' contient 'jour' mais n'est pas temporel → non détecté ✓
      - 'Budget_Par_Jour' → mots {'budget', 'par', 'jour'} → détecté ✓
      - 'DateVente' (CamelCase) → 'Date_Vente' → {'date', 'vente'} → détecté ✓

    Args:
        df: DataFrame pandas à analyser.

    Returns:
        Liste des noms de colonnes temporelles détectées.
    """
    found = []
    temporal_set = set(_TEMPORAL_KEYWORDS)
    for col in df.columns:
        # 1. Split CamelCase : 'DateVente' → 'Date_Vente'
        split_camel = re.sub(r'([a-z])([A-Z])', r'\1_\2', col)
        # 2. Normaliser les séparateurs et découper en mots
        parts = set(
            split_camel.lower()
            .replace("-", "_")
            .replace(" ", "_")
            .split("_")
        )
        # 3. Intersection avec les mots-clés temporels
        if parts & temporal_set:
            found.append(col)
    return found


def _build_seasonality_warnings(
    df: pd.DataFrame,
    corr_pairs: list,
    warnings: list[str],
) -> None:
    """R8 — Ajoute un warning si des colonnes temporelles + corrélations fortes
    sont détectées, signalant un risque de confusion saisonnière.

    Args:
        df: DataFrame pandas à analyser.
        corr_pairs: Liste des paires de corrélations.
        warnings: Liste des warnings à enrichir (modifiée en place).
    """
    temporal_cols = _detect_temporal_columns(df)
    if temporal_cols:
        strong_corrs = [
            p for p in corr_pairs
            if abs(p["value"]) >= 0.6 and p.get("significant_after_correction")
        ]
        if strong_corrs:
            temporal_names = ", ".join(f"'{c}'" for c in temporal_cols)
            warnings.append(
                f"Dimension temporelle détectée ({temporal_names}) : "
                f"les corrélations fortes observées peuvent refléter des "
                f"effets saisonniers plutôt que des relations causales "
                f"directes. Une hausse de prix en été (haute saison) "
                f"apparaît corrélée à la fréquentation, par exemple — "
                f"sans que le prix en soit la cause. Croiser avec une "
                f"analyse par période avant de tirer des conclusions."
            )
