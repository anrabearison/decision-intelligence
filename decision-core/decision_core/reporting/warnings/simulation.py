"""
Warnings de simulation pour decision-core.
"""
from decision_core.stats.regression import validate_regression_inputs
from decision_core.stats.influence_detection import detect_influential_points
from decision_core.models.nonlinearity import StepPatternResult
from .constants import SMALL_SAMPLE_THRESHOLD, LOW_R_SQUARED_THRESHOLD


def _build_simulation_warnings(
    df: pd.DataFrame,
    simulation_config,
    simulation_result: dict,
    n_rows: int,
    warnings: list[str],
    nonlinearity_patterns: list = None,
) -> None:
    """Enrichit les warnings avec les informations sur la simulation.

    Args:
        df: DataFrame pandas à analyser.
        simulation_config: Configuration de la simulation.
        simulation_result: Résultat de la simulation.
        n_rows: Nombre de lignes du dataset.
        warnings: Liste des warnings à enrichir (modifiée en place).
        nonlinearity_patterns: Liste des patterns non-linéaires détectés (optionnel).
    """
    # Vérification de l'échantillon effectif (post-dropna sur les colonnes
    # utilisées) — un dataset de 40 lignes peut n'avoir que 5 valeurs
    # valides sur X et Y.
    effective_sample = validate_regression_inputs(
        df, [simulation_config.feature, simulation_config.target]
    )
    effective_n = len(effective_sample)
    if effective_n < n_rows and effective_n < SMALL_SAMPLE_THRESHOLD:
        warnings.append(
            f"Échantillon effectif réduit pour cette simulation : "
            f"seulement {effective_n} lignes valides sur "
            f"'{simulation_config.feature}' et "
            f"'{simulation_config.target}' (sur {n_rows} au total), "
            f"après retrait des valeurs manquantes - résultats "
            f"indicatifs, pas robustes."
        )

    if simulation_result["model_r_squared"] < LOW_R_SQUARED_THRESHOLD:
        warnings.append(
            f"R² faible ({simulation_result['model_r_squared']:.2f}) pour la "
            f"simulation sur '{simulation_config.feature}' : le modèle "
            f"explique moins de {int(LOW_R_SQUARED_THRESHOLD*100)}% de "
            f"la variance de '{simulation_config.target}' - la projection "
            f"est peu fiable, à interpréter avec beaucoup de prudence."
        )

    influence = detect_influential_points(
        df, feature=simulation_config.feature, target=simulation_config.target
    )
    if influence["indices"]:
        warnings.append(
            f"Point(s) influent(s) détecté(s) (ligne(s) "
            f"{influence['indices']}) : ce résultat dépend fortement "
            f"d'un ou plusieurs points spécifiques - une corrélation "
            f"ou une régression peut être largement déformée par un "
            f"seul point atypique. Vérifier ces valeurs avant de "
            f"s'y fier."
        )

    # Warning spécifique si la feature de simulation fait partie d'une relation non-linéaire
    if nonlinearity_patterns:
        for pattern in nonlinearity_patterns:
            if pattern.feature == simulation_config.feature:
                if isinstance(pattern, StepPatternResult):
                    warnings.append(
                        f"Relation non-linéaire détectée (paliers) entre "
                        f"'{pattern.feature}' et '{pattern.target}' : "
                        f"la simulation linéaire peut être trompeuse sur cette "
                        f"variable. La relation fonctionne par tranches de "
                        f"tarification ou seuils, pas par une droite continue."
                    )
                elif hasattr(pattern, "pattern_type"):
                    if pattern.pattern_type == "u_curve":
                        warnings.append(
                            f"Relation non-linéaire détectée (courbe en U) entre "
                            f"'{pattern.feature}' et '{pattern.target}' : "
                            f"la simulation linéaire peut être trompeuse sur cette "
                            f"variable. Les effets ne sont pas proportionnels - "
                            f"une augmentation de la feature peut avoir un impact "
                            f"différent selon le niveau de départ."
                        )
                    elif pattern.pattern_type == "optimum":
                        warnings.append(
                            f"Relation non-linéaire détectée (optimum) entre "
                            f"'{pattern.feature}' et '{pattern.target}' : "
                            f"la simulation linéaire peut être trompeuse sur cette "
                            f"variable. Il existe un niveau optimal de la feature "
                            f"au-delà duquel l'effet s'inverse - la simulation "
                            f"linéaire ne capture pas cette dynamique."
                        )
