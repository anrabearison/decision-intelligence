"""
Warnings de distribution non-gaussienne pour decision-core.
"""
import pandas as pd
from decision_core.stats.distribution import (
    detect_count_data_distribution,
    detect_zero_inflation,
    detect_heavy_tail,
)


def _build_distribution_warnings(
    df: pd.DataFrame,
    numeric_cols: list[str],
    warnings: list[str],
    summary_threshold: int = 4,
) -> set[str]:
    """Détecte les distributions non-gaussiennes et enrichit les warnings.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        warnings: Liste des warnings à enrichir (modifiée en place).
        summary_threshold: Seuil de nombre de colonnes non-gaussiennes au-delà duquel
            un warning de synthèse est émis à la place des warnings individuels.

    Returns:
        Ensemble des colonnes couvertes par les warnings de distribution (comptage ou zéro-inflated).
    """
    detected_columns = []
    column_details = []

    for col in numeric_cols:
        series = df[col]

        count_result = detect_count_data_distribution(series)
        zero_result = detect_zero_inflation(series)
        heavy_result = detect_heavy_tail(series)

        if count_result is None and zero_result is None and heavy_result is None:
            continue

        column_details.append({
            "column": col,
            "count": count_result,
            "zero": zero_result,
            "heavy": heavy_result,
        })

        if count_result is not None or zero_result is not None:
            detected_columns.append(col)

    if len(column_details) > summary_threshold:
        warnings.append(
            f"Plusieurs variables ({len(column_details)}) présentent des distributions non-gaussiennes "
            f"(comptage, zéro-inflation, queues lourdes). Ces colonnes méritent une attention particulière "
            f"et potentiellement un modèle statistique adapté avant de faire des projections."
        )
        return set(detected_columns)

    for details in column_details:
        col = details["column"]
        count_result = details["count"]
        zero_result = details["zero"]
        heavy_result = details["heavy"]

        if count_result is not None and zero_result is not None:
            warnings.append(
                f"Distribution de comptage avec forte proportion de zéros détectée pour '{count_result.feature}' : "
                f"valeurs discrètes et peu nombreuses ({count_result.unique_values} valeurs distinctes), "
                f"{zero_result.zero_ratio:.0%} des observations sont nulles. "
                f"Une régression gaussienne standard peut sous-estimer ces données ; "
                f"un modèle de comptage zero-inflated ou hurdle est souvent plus adapté."
            )
        elif count_result is not None:
            warnings.append(
                f"Distribution de comptage détectée pour '{count_result.feature}' : "
                f"valeurs discrètes et peu nombreuses ({count_result.unique_values} valeurs distinctes, "
                f"moyenne = {count_result.mean:.2f}, variance = {count_result.variance:.2f}). "
                f"Une régression linéaire normale peut sous-estimer ce type de données ; "
                f"un modèle de comptage (Poisson, quasi-Poisson) est souvent plus adapté."
            )
        elif zero_result is not None:
            warnings.append(
                f"Distribution zéro-inflated détectée pour '{zero_result.feature}' : "
                f"{zero_result.zero_ratio:.0%} des observations sont nulles, ce qui crée une masse importante à zéro. "
                f"La variance n'est pas bien capturée par un modèle gaussien standard ; "
                f"une approche à deux phases (zero-inflated ou hurdle model) peut mieux décrire ces données."
            )

        if heavy_result is not None:
            warnings.append(
                f"Distribution à queue lourde détectée pour '{heavy_result.feature}' : "
                f"forte asymétrie (skew = {heavy_result.skewness:.2f}, kurtosis = {heavy_result.kurtosis:.2f}) et "
                f"valeurs extrêmes influent fortement sur la moyenne. "
                f"Un modèle normal standard peut sous-estimer le risque des très grandes valeurs."
            )

    return set(detected_columns)
