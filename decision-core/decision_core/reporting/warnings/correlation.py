"""
Warnings de corrélation pour decision-core.
"""
from decision_core.stats.profiling import MAX_COLUMNS_FOR_CORRELATION


def _build_correlation_warnings(
    df: pd.DataFrame,
    numeric_cols: list[str],
    corr_pairs: list,
    derived_relationships: set,
    warnings: list[str],
) -> None:
    """Enrichit les warnings avec les informations sur les corrélations.

    Args:
        df: DataFrame pandas à analyser.
        numeric_cols: Liste des colonnes numériques.
        corr_pairs: Liste des paires de corrélations.
        derived_relationships: Ensemble des relations dérivées détectées.
        warnings: Liste des warnings à enrichir (modifiée en place).
    """
    if derived_relationships:
        derived_names = sorted({name for pair in derived_relationships for name in pair})
        warnings.append(
            f"Relation calculée détectée entre {', '.join(derived_names)} : "
            f"une de ces colonnes semble dérivée mathématiquement des "
            f"autres (ex: Total = Prix × Quantité). Leur forte "
            f"corrélation n'est donc pas un insight - c'est une "
            f"conséquence directe du calcul, pas une découverte."
        )

    if len(numeric_cols) > MAX_COLUMNS_FOR_CORRELATION:
        warnings.append(
            f"Dataset large ({len(numeric_cols)} colonnes numériques) : "
            f"les corrélations ne sont calculées que sur les "
            f"{MAX_COLUMNS_FOR_CORRELATION} premières colonnes pour des "
            f"raisons de performance. Les statistiques descriptives "
            f"(moyenne, écart-type...) couvrent en revanche toutes les "
            f"colonnes."
        )

    n_tested = len(corr_pairs)
    n_significant = sum(1 for p in corr_pairs if p.get("significant_after_correction"))
    if n_tested >= 6 and n_significant < n_tested:
        warnings.append(
            f"Comparaisons multiples : sur {n_tested} paires de variables "
            f"testées, seulement {n_significant} restent statistiquement "
            f"significatives après correction (Benjamini-Hochberg, seuil "
            f"5%). Plus il y a de colonnes, plus une corrélation isolée "
            f"forte peut apparaître par hasard - se fier au champ "
            f"'significant_after_correction' de chaque paire plutôt qu'à "
            f"sa seule valeur."
        )
