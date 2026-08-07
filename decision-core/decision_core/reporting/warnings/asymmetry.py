"""
Warnings d'asymétrie F3 pour decision-core.
"""
import pandas as pd
from .constants import ASYMMETRY_THRESHOLD


def _build_asymmetry_warnings(
    df: pd.DataFrame,
    numeric_cols: list[str],
    significant_subgroups: list,
    warnings: list[str],
    simulation_config=None,
    max_warnings: int = 3,
    excluded_columns: list[str] | None = None,
) -> None:
    """Détecte les distributions asymétriques et avertit sans changer la simulation.

    Le ratio |mean - median| / std > ASYMMETRY_THRESHOLD indique une asymétrie significative.
    Avec simulation, l'alerte est limitée à la cible et à la feature du scénario :
    ce sont les seules colonnes qui influencent directement la baseline présentée.
    Sans simulation, l'alerte reste descriptive et limitée aux colonnes les plus
    asymétriques pour éviter de transformer un signal utile en bruit.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        significant_subgroups: Liste des sous-groupes significatifs détectés (pour suggestion).
        warnings: Liste des warnings à enrichir (modifiée en place).
        simulation_config: Configuration de simulation optionnelle.
        max_warnings: Nombre maximum de warnings hors simulation.
        excluded_columns: Colonnes déjà couvertes par les warnings de distribution.
    """
    excluded_columns = set(excluded_columns or [])

    if simulation_config is not None:
        relevant_cols = [
            col for col in [simulation_config.target, simulation_config.feature]
            if col in numeric_cols and col not in excluded_columns
        ]
        limit = len(relevant_cols)
    else:
        relevant_cols = [col for col in numeric_cols if col not in excluded_columns]
        limit = max_warnings

    candidates = []
    for col in relevant_cols:
        mean_val = df[col].mean()
        median_val = df[col].median()
        std_val = df[col].std()

        if std_val > 0:
            asymmetry_ratio = abs(mean_val - median_val) / std_val

            if asymmetry_ratio > ASYMMETRY_THRESHOLD:
                candidates.append((asymmetry_ratio, col, mean_val, median_val))

    for asymmetry_ratio, col, mean_val, median_val in sorted(candidates, reverse=True)[:limit]:
        mean_str = f"{mean_val:,.2f}".replace(",", " ")
        median_str = f"{median_val:,.2f}".replace(",", " ")

        if simulation_config is not None and col == simulation_config.target:
            subject = f"Baseline de simulation peu représentative pour la cible '{col}'"
            interpretation = "La valeur de référence affichée peut ne pas représenter un cas typique."
        elif simulation_config is not None and col == simulation_config.feature:
            subject = f"Point de départ du scénario peu représentatif pour le levier '{col}'"
            interpretation = "Le changement simulé part d'une valeur moyenne qui peut ne pas représenter un cas typique."
        else:
            subject = f"Distribution asymétrique détectée pour '{col}'"
            interpretation = "Résultat à interpréter avec prudence."

        warning = (
            f"{subject} : la moyenne ({mean_str}) "
            f"est très éloignée de la médiane ({median_str}) — quelques gros cas tirent la moyenne "
            f"(ratio asymétrie = {asymmetry_ratio:.2f}, explique {asymmetry_ratio*100:.0f}% des écarts). "
            f"{interpretation} (détail : eta² asymétrie)"
        )

        warnings.append(warning)

    if significant_subgroups and candidates:
        first_subgroup = significant_subgroups[0]
        if isinstance(first_subgroup, dict):
            subgroup_column = first_subgroup.get("column", str(first_subgroup))
        else:
            subgroup_column = str(first_subgroup)
        warning = (
            f"Pour toutes ces colonnes asymétriques, considérez une analyse segmentée "
            f"par '{subgroup_column}' selon l'analyse des sous-groupes, qui montre qu'elle "
            f"segmente fortement les données."
        )
        warnings.append(warning)
