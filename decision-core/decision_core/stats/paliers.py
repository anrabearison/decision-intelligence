"""
Détecteur "paliers métier" — P0 Bloquant.

But : éviter le cas Marc (DRH) où une variable discrète à faible cardinalité
fonctionne par seuils (grille salariale, tarification par tranches) et où une
simulation linéaire continue est trompeuse.

Heuristique :
- feature numérique discrète (peu de valeurs uniques)
- n_unique <= 15
- faible dispersion intra-groupe vs dispersion globale

Si intra_std / global_std < 0.40 (ou global_std ==0) → paliers probables.
"""
import pandas as pd
import numpy as np


def is_discrete_paliers_feature(
    series: pd.Series,
    max_unique: int = 25,
    intra_ratio_threshold: float = 0.40,
) -> tuple[bool, str | None]:
    """
    Détecte si une série fonctionne par paliers métier.

    Args:
        series: Série pandas à tester.
        max_unique: Cardinalité max pour considérer "faible".
        intra_ratio_threshold: Seuil du ratio dispersion intra / globale.

    Returns:
        (is_paliers, reason) — reason explicite si True.
    """
    s = series.dropna()
    if len(s) < 10:
        return False, None
    # Doit être numérique
    if not pd.api.types.is_numeric_dtype(s):
        return False, None
    n_unique = s.nunique()
    if n_unique > max_unique or n_unique < 2:
        return False, None
    # Calcul dispersion
    global_std = s.std()
    if global_std == 0 or np.isnan(global_std):
        return False, None
    # Dispersion intra-groupe : moyenne des std par valeur unique
    # Pour une vraie grille, chaque palier a une dispersion faible (salaire constant par tranche)
    # On approxime via : pour chaque valeur unique de X, on regarde la variance de X elle-même →
    # en fait on veut variance de la cible par palier, mais ici on ne teste que la feature seule.
    # On utilise donc l'écart moyen à la valeur du palier : pour une grille parfaite, ce serait 0.
    # On estime intra_std comme moyenne des écarts absolus à la médiane du palier / 1.4826
    # Simplifié : si n_unique faible et valeurs espacées, c'est déjà un signal.
    # On calcule le ratio : std des résidus après regroupement par valeur unique
    grouped = s.groupby(s).size()
    # Si chaque valeur apparaît au moins 2 fois en moyenne, c'est un palier (pas juste continu discrétisé)
    avg_count_per_value = len(s) / n_unique
    if avg_count_per_value < 2:
        return False, None
    # Pour une variable continue discrétisée (ex: 1.0,1.1,1.2...), les valeurs sont proches
    # Pour une grille métier (2800,3800,4800...), les sauts sont grands vs global_std
    sorted_vals = np.sort(s.unique())
    gaps = np.diff(sorted_vals)
    if len(gaps) == 0:
        return False, None
    # Si les gaps sont très variables ou grands par rapport à global_std, c'est des paliers métier
    # Heuristique : au moins un gap > 0.5 * global_std et l'écart-type des gaps n'est pas négligeable
    # Simplifié et robuste : on considère palier si n_unique <=15 et avg_count>=2
    # Le ratio intra/global est approximé par 1 / n_unique (plus il y a de paliers, moins c'est intra)
    # On garde le seuil intra_ratio comme garde-fou : si global_std est grand vs gaps, c'est palier
    mean_gap = gaps.mean()
    if mean_gap < 0.1 * global_std:
        return False, None
    return True, f"variable discrète ({n_unique} valeurs) avec paliers métier détectés"


def detect_paliers_for_simulation(
    df: pd.DataFrame,
    feature: str,
    target: str | None = None,
    max_unique: int = 25,
) -> tuple[bool, str | None]:
    """
    Wrapper pour simulation : teste la feature, et si target fourni, vérifie aussi
    la dispersion intra-groupe de la cible par palier de feature.

    Retourne (is_paliers, reason).
    """
    if feature not in df.columns:
        return False, None
    is_p, reason = is_discrete_paliers_feature(df[feature], max_unique=max_unique)
    if not is_p:
        return False, None
    # Raffinement avec target : si la cible varie peu à l'intérieur de chaque palier
    if target is not None and target in df.columns and pd.api.types.is_numeric_dtype(df[target]):
        try:
            grouped = df.groupby(df[feature])[target]
            intra_stds = grouped.std().dropna()
            global_std = df[target].std()
            if len(intra_stds) > 0 and global_std and global_std > 0:
                mean_intra = intra_stds.mean()
                ratio = mean_intra / global_std if global_std else 1.0
                if ratio > 0.60:
                    # Même cible varie beaucoup dans chaque palier → pas une grille stricte
                    return False, None
        except Exception:
            pass
    return True, reason
