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
    Attention : si baseline_feature_value = 0.0, la variation appliquée sera
    nulle (0 × (1 + change_pct) = 0) — la simulation retourne la même valeur
    que la baseline. Ce comportement est mathématiquement correct ; préférer
    une valeur epsilon strictement positive si ce cas est possible.
  - bounds : tuple (min_val, max_val) bornes physiques ou institutionnelles
    pour clipper le résultat simulé (ex : (0, 20) pour une note sur 20).
    La baseline n'est pas affectée par les bornes. Lève ValueError si
    min_val > max_val.
"""
from decision_core.regression import fit_simple_regression
from decision_core.models import SimulationConfig, SimulationResult
import pandas as pd


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
) -> SimulationResult:
    """Simule l'impact d'une variation en % d'une feature sur la cible.

    Args:
        df: DataFrame source.
        target: Nom de la colonne cible à prédire.
        feature: Nom de la colonne feature sur laquelle appliquer la variation.
        change_pct: Variation relative (ex : 0.10 pour +10%).
        baseline_feature_value: Valeur de référence de la feature (optionnel).
        bounds: Tuple (min_val, max_val) pour borner le résultat simulé (optionnel).

    Returns:
        SimulationResult encapsulant les résultats de la simulation.
    """
    config = SimulationConfig(
        target=target,
        feature=feature,
        change_pct=change_pct,
        baseline_feature_value=baseline_feature_value,
        bounds=bounds,
    )

    model = fit_simple_regression(df, target=config.target, feature=config.feature)

    ref_feature_value = (
        config.baseline_feature_value
        if config.baseline_feature_value is not None
        else df[config.feature].mean()
    )

    baseline = model.intercept + model.slope * ref_feature_value
    simulated_feature_value = ref_feature_value * (1 + config.change_pct)
    simulated = model.intercept + model.slope * simulated_feature_value

    bounds_applied: bool | None = None
    if config.bounds is not None:
        min_val, max_val = float(config.bounds[0]), float(config.bounds[1])
        bounds_applied = not (min_val <= simulated <= max_val)
        simulated = max(min_val, min(max_val, simulated))

    target_std = df[config.target].std()
    is_reliable = target_std == 0 or abs(baseline) >= NEAR_ZERO_BASELINE_RATIO * target_std

    change_pct_result = (
        (simulated - baseline) / baseline * 100 if is_reliable else None
    )

    return SimulationResult(
        baseline=float(baseline),
        simulated=float(simulated),
        change_pct=float(change_pct_result) if change_pct_result is not None else None,
        change_pct_reliable=bool(is_reliable),
        model_r_squared=model.r_squared,
        feature=config.feature,
        target=config.target,
        bounds_applied=bounds_applied,
    )


