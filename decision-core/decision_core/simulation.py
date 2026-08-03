"""
Module de simulation - Phase 1a.
Scénario simple : variation en % d'une variable, impact estimé via
régression linéaire simple. Le vrai Monte Carlo (distributions,
corrélations, 10 000 itérations) appartient à la Phase 1b.

Robustesse : quand le baseline (valeur de référence de la cible) est
proche de zéro relativement à la dispersion de la variable, un
pourcentage de variation devient statistiquement trompeur (un petit
écart absolu produit un pourcentage énorme) - change_pct_reliable
signale explicitement ce cas plutôt que de renvoyer un chiffre qui a
l'air valide mais ne l'est pas (bug trouvé en testant sur un cas de
signal quasi nul, cf. README).

Paramètres optionnels ajoutés (Phase 1a - refonte) :
  - baseline_feature_value : valeur de référence de la feature (ex : dernière
    valeur connue du client). Si absent, la moyenne historique est utilisée.
  - bounds : tuple (min_val, max_val) bornes physiques ou institutionnelles
    pour clipper le résultat simulé (ex : note entre 0 et 20).
"""
import pandas as pd
from decision_core.regression import fit_simple_regression

# Si |baseline| est sous ce seuil relatif à l'écart-type de la cible,
# un pourcentage de variation n'est pas jugé fiable.
NEAR_ZERO_BASELINE_RATIO = 0.1


def simulate_scenario(
    df: pd.DataFrame,
    target: str,
    feature: str,
    change_pct: float,
    baseline_feature_value: float | None = None,
    bounds: tuple[float, float] | None = None,
) -> dict:
    """Simule l'impact d'une variation en % d'une feature sur la cible.

    Args:
        df: DataFrame source.
        target: Nom de la colonne cible à prédire.
        feature: Nom de la colonne feature sur laquelle appliquer la variation.
        change_pct: Variation relative (ex : 0.10 pour +10%).
        baseline_feature_value: Valeur de référence de la feature (optionnel).
            Si fourni, remplace la moyenne historique comme point de départ.
            Utile pour partir de la dernière valeur connue plutôt que de la
            moyenne sur l'ensemble de l'historique.
        bounds: Tuple (min_val, max_val) pour borner le résultat simulé
            (optionnel). Exemple : (0, 20) pour une note sur 20. Le résultat
            simulé est clippé à ces bornes ; la baseline n'est pas affectée.

    Returns:
        Dict contenant baseline, simulated, change_pct, change_pct_reliable,
        model_r_squared, feature, target, et optionnellement bounds_applied.
    """
    model = fit_simple_regression(df, target=target, feature=feature)

    # R2 : utiliser la valeur fournie si disponible, sinon la moyenne historique
    ref_feature_value = (
        baseline_feature_value
        if baseline_feature_value is not None
        else df[feature].mean()
    )

    baseline = model["intercept"] + model["slope"] * ref_feature_value
    simulated_feature_value = ref_feature_value * (1 + change_pct)
    simulated = model["intercept"] + model["slope"] * simulated_feature_value

    # R4 : clipper le résultat simulé aux bornes physiques/institutionnelles
    bounds_applied = False
    if bounds is not None:
        min_val, max_val = bounds
        clipped = max(float(min_val), min(float(max_val), simulated))
        if clipped != simulated:
            bounds_applied = True
        simulated = clipped

    target_std = df[target].std()
    is_reliable = target_std == 0 or abs(baseline) >= NEAR_ZERO_BASELINE_RATIO * target_std

    change_pct_result = (
        (simulated - baseline) / baseline * 100 if is_reliable else None
    )

    result = {
        "baseline": float(baseline),
        "simulated": float(simulated),
        "change_pct": float(change_pct_result) if change_pct_result is not None else None,
        "change_pct_reliable": bool(is_reliable),
        "model_r_squared": model["r_squared"],
        "feature": feature,
        "target": target,
    }

    if bounds is not None:
        result["bounds_applied"] = bounds_applied

    return result
