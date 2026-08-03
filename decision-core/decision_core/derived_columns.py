"""
Module de détection de colonnes dérivées - Phase 1a.

Une colonne calculée à partir d'autres colonnes du même fichier
(ex: Total = Prix * Quantité, Profit = Revenu - Cout) produit
mécaniquement une corrélation très forte avec ses composantes - ce
n'est jamais un insight statistique, c'est une tautologie
arithmétique. Sans cette détection, generate_report présenterait
cette relation comme "la corrélation la plus forte", trompant
l'utilisateur en lui faisant croire à une découverte (trouvé en test
de lisibilité simulé).

Détecte les relations de produit, somme et différence entre triplets
de colonnes numériques - les formes les plus courantes en données
métier (Total=Prix*Quantité, Marge=Revenu-Cout, Total=SousTotalA+
SousTotalB).
"""
import itertools
import numpy as np
import pandas as pd

# Tolérance relative pour juger une relation "exacte" malgré de petits
# écarts d'arrondi réalistes (saisie manuelle, conversion de devise...).
RELATIVE_TOLERANCE = 0.02

# La recherche de triplets est en O(k^3) (k = nombre de colonnes) :
# mesuré à 26s pour 50 colonnes avant optimisation, inacceptable en
# synchrone HTTP. Après conversion en numpy en amont (élimine l'overhead
# pandas répété par paire), le plafond reste nécessaire au-delà de ce
# nombre de colonnes - cohérent avec la même leçon déjà tirée pour
# MAX_COLUMNS_FOR_CORRELATION (profiling.py).
MAX_COLUMNS_FOR_DERIVED_DETECTION = 30


def _matches_within_tolerance(actual: np.ndarray, predicted: np.ndarray) -> bool:
    # Exclure les lignes avec NaN (sur l'une ou l'autre valeur) de la
    # comparaison plutôt que de les compter comme "ne correspond pas" -
    # une comparaison impliquant NaN vaut toujours False en numpy, donc
    # quelques valeurs manquantes suffisaient à faire chuter le taux de
    # correspondance sous le seuil, ratant une vraie relation dérivée
    # sur des données par ailleurs propres (trouvé sur données réelles).
    valid_mask = ~(np.isnan(actual) | np.isnan(predicted))
    if valid_mask.sum() < 3:
        return False
    actual = actual[valid_mask]
    predicted = predicted[valid_mask]

    # Écart relatif à l'échelle des valeurs, pas un seuil absolu fixe -
    # une tolérance de 2% a du sens aussi bien pour des montants en
    # centaines que pour des quantités à deux chiffres.
    scale = np.maximum(np.abs(actual), 1e-9)
    relative_error = np.abs(actual - predicted) / scale
    return bool(np.mean(relative_error < RELATIVE_TOLERANCE) > 0.95)


def detect_derived_relationships(df: pd.DataFrame, numeric_cols: list) -> set:
    """Détecte les relations de colonnes dérivées (produit, somme, différence).

    Args:
        df: DataFrame pandas contenant les données.
        numeric_cols: Liste des colonnes numériques à analyser.

    Returns:
        Ensemble de frozenset({colA, colB}) pour chaque paire de colonnes
        liées par une relation dérivée (l'une des deux entre dans le calcul
        de l'autre via une troisième colonne du fichier).
    """
    cols = numeric_cols[:MAX_COLUMNS_FOR_DERIVED_DETECTION]

    # Conversion unique en numpy : évite l'overhead d'indexation pandas
    # répété des millions de fois dans la boucle triple ci-dessous -
    # c'est ce qui dominait le temps d'exécution, pas le calcul lui-même.
    arrays = {col: df[col].values.astype(float) for col in cols}

    derived_pairs = set()
    for target in cols:
        target_arr = arrays[target]
        others = [c for c in cols if c != target]
        for a, b in itertools.combinations(others, 2):
            a_arr, b_arr = arrays[a], arrays[b]
            if (
                _matches_within_tolerance(target_arr, a_arr * b_arr)
                or _matches_within_tolerance(target_arr, a_arr + b_arr)
                or _matches_within_tolerance(target_arr, a_arr - b_arr)
                or _matches_within_tolerance(target_arr, b_arr - a_arr)
            ):
                derived_pairs.add(frozenset([target, a]))
                derived_pairs.add(frozenset([target, b]))

    return derived_pairs
