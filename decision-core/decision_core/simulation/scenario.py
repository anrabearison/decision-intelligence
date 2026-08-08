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
from decision_core.stats.regression import fit_simple_regression
from decision_core.models import SimulationConfig, SimulationResult
import numpy as np
import pandas as pd


# Si |baseline| est sous ce seuil relatif à l'écart-type de la cible,
# un pourcentage de variation n'est pas jugé fiable.
NEAR_ZERO_BASELINE_RATIO = 0.1


def _predict_from_model(model, feature_value: float) -> float:
    """Retourne une prédiction bornée correctement selon le type de modèle."""
    if getattr(model, "model_type", None) == "logistic":
        z = model.intercept + model.coefficient * feature_value
        z = np.clip(z, -500, 500)
        return float(1 / (1 + np.exp(-z)))
    return float(model.intercept + model.slope * feature_value)


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

    baseline = _predict_from_model(model, ref_feature_value)
    simulated_feature_value = ref_feature_value * (1 + config.change_pct)
    simulated = _predict_from_model(model, simulated_feature_value)

    bounds_applied: bool | None = None
    if config.bounds is not None:
        min_val, max_val = float(config.bounds[0]), float(config.bounds[1])
        bounds_applied = not (min_val <= simulated <= max_val)
        simulated = max(min_val, min(max_val, simulated))

    target_std = df[config.target].std()
    model_type = getattr(model, "model_type", "linear")
    is_probability_model = model_type == "logistic"
    is_reliable = (
        not is_probability_model
        and (target_std == 0 or abs(baseline) >= NEAR_ZERO_BASELINE_RATIO * target_std)
    )

    change_pct_result = (
        (simulated - baseline) / baseline * 100 if is_reliable else None
    )
    change_absolute = simulated - baseline
    change_percentage_points = change_absolute * 100 if is_probability_model else None

    # P0-2 : actionable flag — R² quasi nul ou paliers métier rendent la simulation non actionnable
    actionable = True
    non_actionable_reason = None
    if model.r_squared < 0.01:
        actionable = False
        non_actionable_reason = (
            f"R² très faible ({model.r_squared:.3f}) : la feature '{feature}' n'explique "
            f"quasiment pas la variance de '{target}'. La simulation globale n'est pas exploitable."
        )
    else:
        # Détection paliers métier sur la feature
        try:
            from decision_core.stats.paliers import detect_paliers_for_simulation

            is_paliers, _ = detect_paliers_for_simulation(df, feature, target)
            if is_paliers:
                actionable = False
                non_actionable_reason = (
                    f"La variable '{feature}' semble fonctionner par paliers/seuils métier. "
                    f"Une simulation continue en pourcentage est trompeuse — préférez une simulation par passage de tranche."
                )
        except Exception:
            pass

    # P3-12 : intervalle d'incertitude (prediction interval à 80%)
    prediction_interval = None
    try:
        clean = df[[feature, target]].dropna()
        x = clean[feature].values
        y = clean[target].values
        # Résidus du modèle
        if model_type == "logistic":
            # Pour logistique, intervalle sur probabilité via écart-type des prédictions
            p = 1 / (1 + np.exp(-np.clip(model.intercept + model.coefficient * x, -500, 500)))
            resid_std = float(np.std(y - p)) if len(y) > 1 else 0.0
            delta = 1.28 * resid_std  # ~80% interval
            prediction_interval = {
                "lower": float(max(0.0, min(1.0, simulated - delta))),
                "upper": float(max(0.0, min(1.0, simulated + delta))),
                "confidence": 0.80,
            }
        else:
            y_pred = model.intercept + model.slope * x
            resid_std = float(np.std(y - y_pred)) if len(y) > 1 else 0.0
            delta = 1.28 * resid_std
            prediction_interval = {
                "lower": float(simulated - delta),
                "upper": float(simulated + delta),
                "confidence": 0.80,
            }
            if config.bounds is not None:
                lo, hi = float(config.bounds[0]), float(config.bounds[1])
                prediction_interval["lower"] = max(lo, prediction_interval["lower"])
                prediction_interval["upper"] = min(hi, prediction_interval["upper"])
    except Exception:
        prediction_interval = None

    # P3-13 : validation croisée prédictive (5-fold si n>=20)
    cross_validation = None
    try:
        clean = df[[feature, target]].dropna()
        n = len(clean)
        if n >= 20 and model_type != "logistic":
            # 5-fold CV simple
            idx = np.arange(n)
            np.random.seed(0)
            np.random.shuffle(idx)
            fold = n // 5
            r2_list = []
            for k in range(5):
                test_idx = idx[k * fold : (k + 1) * fold if k < 4 else n]
                train_idx = np.setdiff1d(idx, test_idx)
                x_train, y_train = clean[feature].values[train_idx], clean[target].values[train_idx]
                x_test, y_test = clean[feature].values[test_idx], clean[target].values[test_idx]
                if len(x_train) < 3 or len(x_test) < 2:
                    continue
                slope, intercept, r_val, _, _ = stats.linregress(x_train, y_train)
                y_pred = intercept + slope * x_test
                ss_res = np.sum((y_test - y_pred) ** 2)
                ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                r2_list.append(r2)
            if r2_list:
                cv_r2_mean = float(np.mean(r2_list))
                # MAE/RMSE sur tout le dataset en holdout approx
                y_pred_all = model.intercept + model.slope * clean[feature].values if model_type != "logistic" else 1/(1+np.exp(-np.clip(model.intercept + model.coefficient * clean[feature].values, -500,500)))
                mae = float(np.mean(np.abs(clean[target].values - y_pred_all)))
                rmse = float(np.sqrt(np.mean((clean[target].values - y_pred_all) ** 2)))
                cross_validation = {"cv_r2_mean": cv_r2_mean, "mae": mae, "rmse": rmse, "folds": 5}
    except Exception:
        cross_validation = None

    # P3-15 : warnings structurés
    warnings_structured = []
    try:
        if not actionable and non_actionable_reason:
            code = "SIMULATION_NON_ACTIONABLE_R2" if "R²" in non_actionable_reason else "SIMULATION_PALIERS"
            warnings_structured.append({
                "code": code,
                "severity": "high",
                "category": "simulation",
                "columns": [feature, target],
                "message": non_actionable_reason,
                "recommendation": "Préférez une analyse segmentée ou par tranche avant de décider.",
            })
        if model.r_squared < 0.05 and actionable:
            warnings_structured.append({
                "code": "SIMULATION_LOW_R2",
                "severity": "medium",
                "category": "simulation",
                "columns": [feature, target],
                "message": f"R² faible ({model.r_squared:.2f})",
                "recommendation": "Interprétez avec prudence.",
            })
    except Exception:
        pass

    return SimulationResult(
        baseline=float(baseline),
        simulated=float(simulated),
        change_pct=float(change_pct_result) if change_pct_result is not None else None,
        change_pct_reliable=bool(is_reliable),
        model_r_squared=model.r_squared,
        feature=config.feature,
        target=config.target,
        change_absolute=float(change_absolute),
        change_percentage_points=(
            float(change_percentage_points) if change_percentage_points is not None else None
        ),
        model_type=model_type,
        bounds_applied=bounds_applied,
        actionable=actionable,
        non_actionable_reason=non_actionable_reason,
        prediction_interval=prediction_interval,
        cross_validation=cross_validation,
        warnings_structured=warnings_structured if warnings_structured else None,
    )
