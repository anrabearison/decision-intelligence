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
"""
import pandas as pd
from decision_core.regression import fit_simple_regression

# Si |baseline| est sous ce seuil relatif à l'écart-type de la cible,
# un pourcentage de variation n'est pas jugé fiable.
NEAR_ZERO_BASELINE_RATIO = 0.1


def simulate_scenario(df: pd.DataFrame, target: str, feature: str, change_pct: float) -> dict:
    model = fit_simple_regression(df, target=target, feature=feature)

    baseline_feature_value = df[feature].mean()
    baseline = model["intercept"] + model["slope"] * baseline_feature_value

    simulated_feature_value = baseline_feature_value * (1 + change_pct)
    simulated = model["intercept"] + model["slope"] * simulated_feature_value

    target_std = df[target].std()
    is_reliable = target_std == 0 or abs(baseline) >= NEAR_ZERO_BASELINE_RATIO * target_std

    change_pct_result = (
        (simulated - baseline) / baseline * 100 if is_reliable else None
    )

    return {
        "baseline": float(baseline),
        "simulated": float(simulated),
        "change_pct": float(change_pct_result) if change_pct_result is not None else None,
        "change_pct_reliable": bool(is_reliable),
        "model_r_squared": model["r_squared"],
        "feature": feature,
        "target": target,
    }
