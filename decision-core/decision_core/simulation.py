"""
Module de simulation - Phase 1a.
Scénario simple : variation en % d'une variable, impact estimé via
régression linéaire simple. Le vrai Monte Carlo (distributions,
corrélations, 10 000 itérations) appartient à la Phase 1b.
"""
import pandas as pd
from decision_core.regression import fit_simple_regression


def simulate_scenario(df: pd.DataFrame, target: str, feature: str, change_pct: float) -> dict:
    model = fit_simple_regression(df, target=target, feature=feature)

    baseline_feature_value = df[feature].mean()
    baseline = model["intercept"] + model["slope"] * baseline_feature_value

    simulated_feature_value = baseline_feature_value * (1 + change_pct)
    simulated = model["intercept"] + model["slope"] * simulated_feature_value

    change_pct_result = (simulated - baseline) / baseline * 100 if baseline != 0 else float("nan")

    return {
        "baseline": float(baseline),
        "simulated": float(simulated),
        "change_pct": float(change_pct_result),
        "model_r_squared": model["r_squared"],
        "feature": feature,
        "target": target,
    }
