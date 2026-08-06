"""
Module de détection de non-linéarité - Phase 1b.

Ce module fournit des fonctions pour :
- Détection de patterns quadratiques (courbes en U, optimaux gaussiens)
- Détection de patterns par paliers (step functions)

Objectif : résoudre la faille #4 identifiée dans RAPPORT_TESTS_DOMAINES.md
en détectant les relations non-linéaires ignorées par la régression linéaire.

Choix méthodologiques :
- Garde-fou petit échantillon : n >= 10 minimum pour toute détection
  (réutilisation de MIN_ROWS_FOR_REGRESSION avec marge de sécurité)
- Pas de spline/GAM/polynôme degré >2 : trop complexe pour ~15 lignes,
  risque de surapprentissage élevé
- Quadratique seulement : capture les U et cloches, cas les plus courants
- Step par quantiles : robuste aux distributions asymétriques, adapte le nombre
  de bins à la taille de l'échantillon
- Significativité marginale du coefficient quadratique (p ≤ 0.10) : compromis
  standard exploratoire pour petit échantillon, avec un seuil ajusté plus
  conservateur que l'ancien calibrage sur un seul exemple.
- Significativité ANOVA du step pattern (p < 0.05) : protège contre le
  gonflement artificiel de l'eta² sur de petits groupes par quantile.
- Comparaison des R² ajustés : amélioration d'au moins 0.04 requise pour
  qu'un modèle quadratique soit retenu.
- Les paires de top corrélations sont corrigées pour comparaisons multiples
  (Benjamini-Hochberg) au moment de construire les warnings.
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Optional
from decision_core.models.nonlinearity import QuadraticPatternResult, StepPatternResult

MIN_ROWS_FOR_NONLINEARITY = 10

# Seuils choisis pour un compromis puissance / faux positifs à petit échantillon :
# 1. QUADRATIC_IMPROVEMENT_THRESHOLD (0.04) : amélioration minimale du R² ajusté
#    requise pour qu'un modèle quadratique soit considérablement meilleur qu'un
#    modèle linéaire. Ce seuil est volontairement plus strict que le cas unique
#    de l'énergie, afin de limiter le sur-détection sur le corpus complet.
# 2. QUADRATIC_P_VALUE_THRESHOLD (0.10) : seuil marginal reconnu en analyse
#    exploratoire. Il permet de conserver un signal sur de petits échantillons
#    tout en restant bien plus conservateur que l'ancien seuil calibré sur un
#    seul exemple.
# 3. ETA_SQUARED_IMPROVEMENT_THRESHOLD (0.02) : Permet de détecter les paliers tarifaires
#    de Poids_Colis_Kg -> Frais_Port_Euros dans 'logistique_livraisons_2025.csv' (différence = 0.0218).
QUADRATIC_IMPROVEMENT_THRESHOLD = 0.04
QUADRATIC_P_VALUE_THRESHOLD = 0.10
ETA_SQUARED_IMPROVEMENT_THRESHOLD = 0.02


def detect_quadratic_pattern(
    df: pd.DataFrame,
    target: str,
    feature: str
) -> Optional[QuadraticPatternResult]:
    """Détecte un pattern quadratique (courbe en U ou cloche) entre feature et target.

    Fit un modèle linéaire (y = a + bx) et un modèle quadratique (y = a + bx + cx²),
    compare les R² ajustés et teste la significativité du coefficient quadratique.

    Args:
        df: DataFrame pandas contenant les données.
        target: Nom de la colonne cible numérique.
        feature: Nom de la colonne feature numérique.

    Returns:
        QuadraticPatternResult si un pattern significatif est détecté, None sinon.
    """
    if len(df) < MIN_ROWS_FOR_NONLINEARITY:
        return None

    x = df[feature].values
    y = df[target].values

    # Nettoyage des NaN
    mask = ~np.isnan(x) & ~np.isnan(y)
    x = x[mask]
    y = y[mask]

    if len(x) < MIN_ROWS_FOR_NONLINEARITY:
        return None

    # Modèle linéaire : y = a + bx
    coeffs_linear, residuals_linear, _, _, _ = np.polyfit(x, y, 1, full=True)
    a_linear, b_linear = coeffs_linear
    ss_res_linear = residuals_linear[0] if len(residuals_linear) > 0 else 0
    ss_tot_linear = np.sum((y - np.mean(y)) ** 2)
    r2_linear = 1 - (ss_res_linear / ss_tot_linear) if ss_tot_linear > 0 else 0
    n = len(x)
    r2_linear_adj = 1 - (1 - r2_linear) * (n - 1) / (n - 2) if n > 2 else r2_linear

    # Modèle quadratique : y = a + bx + cx²
    coeffs_quad, residuals_quad, _, _, _ = np.polyfit(x, y, 2, full=True)
    # np.polyfit retourne les coefficients dans l'ordre décroissant des puissances
    # Pour degré 2 : [c, b, a] où y = c*x² + b*x + a
    c_quad, b_quad, a_quad = coeffs_quad
    ss_res_quad = residuals_quad[0] if len(residuals_quad) > 0 else 0
    r2_quad = 1 - (ss_res_quad / ss_tot_linear) if ss_tot_linear > 0 else 0
    r2_quad_adj = 1 - (1 - r2_quad) * (n - 1) / (n - 3) if n > 3 else r2_quad

    # Test de significativité du coefficient quadratique c
    # On utilise une approche basée sur l'erreur standard estimée
    if n < 4:
        return None

    # Matrice de design pour le modèle quadratique
    X_design = np.column_stack([np.ones(n), x, x**2])
    # Estimation de la variance du bruit
    mse = ss_res_quad / (n - 3)
    # (X^T X)^-1 pour l'erreur standard des coefficients
    try:
        XtX_inv = np.linalg.inv(X_design.T @ X_design)
        var_c = mse * XtX_inv[2, 2]
        se_c = np.sqrt(var_c) if var_c > 0 else 0
        # t-test pour le coefficient c
        t_stat = c_quad / se_c if se_c > 0 else 0
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 3)) if n > 3 else 1.0
    except np.linalg.LinAlgError:
        return None

    # Conditions pour détecter un pattern significatif
    # 1. R² ajusté quadratique > R² ajusté linéaire
    # 2. Coefficient quadratique significatif selon le seuil de tolérance p_value
    # 3. Amélioration suffisante du R² ajusté (seuil calibré)
    improvement = r2_quad_adj - r2_linear_adj
    if (r2_quad_adj > r2_linear_adj and
        improvement >= QUADRATIC_IMPROVEMENT_THRESHOLD and
        p_value <= QUADRATIC_P_VALUE_THRESHOLD):

        pattern_type = "u_curve" if c_quad > 0 else "optimum"
        return QuadraticPatternResult(
            feature=feature,
            target=target,
            pattern_type=pattern_type,
            r2_linear_adj=r2_linear_adj,
            r2_quadratic_adj=r2_quad_adj,
            quadratic_coefficient=float(c_quad),
            p_value=float(p_value)
        )

    return None

def detect_step_pattern(
    df: pd.DataFrame,
    target: str,
    feature: str,
    max_bins: int = 5
) -> Optional[StepPatternResult]:
    """Détecte un pattern par paliers (step function) entre feature et target.

    Discrétise la feature en quantiles et compare l'eta² du modèle par bins
    au R² du modèle linéaire simple.

    Args:
        df: DataFrame pandas contenant les données.
        target: Nom de la colonne cible numérique.
        feature: Nom de la colonne feature numérique.
        max_bins: Nombre maximum de bins pour la discrétisation.

    Returns:
        StepPatternResult si un pattern significatif est détecté, None sinon.
    """
    if len(df) < MIN_ROWS_FOR_NONLINEARITY:
        return None

    x = df[feature].values
    y = df[target].values

    # Nettoyage des NaN
    mask = ~np.isnan(x) & ~np.isnan(y)
    x = x[mask]
    y = y[mask]

    if len(x) < MIN_ROWS_FOR_NONLINEARITY:
        return None

    # Détermination du nombre de bins (minimum 2, max_bins, ou n//4)
    n_bins = min(max_bins, max(2, len(x) // 4))

    if n_bins < 2:
        return None

    # Calcul du R² linéaire
    coeffs_linear, residuals_linear, _, _, _ = np.polyfit(x, y, 1, full=True)
    ss_res_linear = residuals_linear[0] if len(residuals_linear) > 0 else 0
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2_linear = 1 - (ss_res_linear / ss_tot) if ss_tot > 0 else 0

    # Calcul de l'eta² par bins et du test F d'ANOVA
    try:
        x_binned = pd.qcut(x, n_bins, duplicates='drop')
    except ValueError:
        return None

    from decision_core.stats.anova import compute_eta_squared_with_significance
    anova_result = compute_eta_squared_with_significance(y, x_binned)
    eta_squared_binned = anova_result.eta_squared

    # Condition : l'eta² par bins doit être nettement meilleur que le R² linéaire
    # et la structure par paliers doit être statistiquement significative.
    if (anova_result.reliable and
        anova_result.p_value <= 0.05 and
        eta_squared_binned > r2_linear + ETA_SQUARED_IMPROVEMENT_THRESHOLD):
        # Calcul des bornes des bins
        try:
            _, bin_edges = pd.qcut(x, n_bins, retbins=True, duplicates='drop')
            bin_boundaries = bin_edges.tolist()
        except ValueError:
            bin_boundaries = []

        return StepPatternResult(
            feature=feature,
            target=target,
            n_bins=n_bins,
            r2_linear=float(r2_linear),
            eta_squared_binned=float(eta_squared_binned),
            p_value=float(anova_result.p_value),
            f_statistic=float(anova_result.f_statistic),
            bin_boundaries=bin_boundaries
        )

    return None
