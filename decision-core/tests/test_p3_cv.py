"""
Tests P3-13 : Validation croisée pour les simulations.
"""
import pytest
import pandas as pd
import numpy as np
from decision_core.simulation.scenario import simulate_scenario
from decision_core.models import SimulationConfig


def test_cv_aissa_returns_low_r2():
    """Aïssa (n=130) → cv_r2_mean ≈ 0.00 ±0.05, CV non-None."""
    np.random.seed(42)
    df = pd.DataFrame({
        "Budget_Pub": np.random.uniform(0, 1000, 130),
        "CA": np.random.normal(5000, 1000, 130),
    })
    sim_config = SimulationConfig(target="CA", feature="Budget_Pub", change_pct=0.10)
    result = simulate_scenario(df, target=sim_config.target, feature=sim_config.feature, change_pct=sim_config.change_pct)
    
    assert result.cross_validation is not None
    assert result.cross_validation["cv_r2_mean"] < 0.1  # R² très faible
    assert result.cross_validation["folds"] == 5
    assert result.cross_validation["n"] == 130
    assert "mae" in result.cross_validation
    assert "rmse" in result.cross_validation


def test_cv_marc_returns_good_r2():
    """Marc (n=115, grille) → cv_r2_mean ≈ 0.80, CV non-None."""
    np.random.seed(42)
    anc = np.random.randint(1, 20, 115)
    df = pd.DataFrame({
        "Anciennete": anc,
        "Salaire": 2800 + 1000 * (anc // 5),  # Grille par paliers
    })
    sim_config = SimulationConfig(target="Salaire", feature="Anciennete", change_pct=0.20)
    result = simulate_scenario(df, target=sim_config.target, feature=sim_config.feature, change_pct=sim_config.change_pct)
    
    assert result.cross_validation is not None
    assert result.cross_validation["cv_r2_mean"] > 0.5  # R² bon
    assert result.cross_validation["mae"] > 0
    assert result.cross_validation["rmse"] > 0


def test_cv_karim_returns_none_small_sample():
    """Karim (n=18) → None (trop petit, n<20)."""
    np.random.seed(42)
    poids = np.random.normal(30, 5, 18)
    df = pd.DataFrame({
        "Poids": poids,
        "Taux": poids * 0.5 + np.random.normal(15, 2, 18),
    })
    sim_config = SimulationConfig(target="Taux", feature="Poids", change_pct=0.10)
    result = simulate_scenario(df, target=sim_config.target, feature=sim_config.feature, change_pct=sim_config.change_pct)
    
    assert result.cross_validation is None  # n < 20


def test_cv_skips_logistic():
    """Logistique → None (déjà log_loss/calibration ailleurs)."""
    np.random.seed(42)
    df = pd.DataFrame({
        "Feature": np.random.uniform(0, 1, 50),
        "Target": np.random.choice([0, 1], 50),
    })
    sim_config = SimulationConfig(target="Target", feature="Feature", change_pct=0.10)
    result = simulate_scenario(df, target=sim_config.target, feature=sim_config.feature, change_pct=sim_config.change_pct)
    
    assert result.cross_validation is None  # model_type == "logistic"


def test_cv_r2_clipped_positive():
    """CV_R² négatif est clippé à 0 pour user-friendly."""
    np.random.seed(42)
    # Dataset avec très peu de signal → R² peut être négatif
    df = pd.DataFrame({
        "Feature": np.random.normal(0, 1, 100),
        "Target": np.random.normal(0, 1, 100),  # Pas de corrélation
    })
    sim_config = SimulationConfig(target="Target", feature="Feature", change_pct=0.10)
    result = simulate_scenario(df, target=sim_config.target, feature=sim_config.feature, change_pct=sim_config.change_pct)
    
    if result.cross_validation is not None:
        assert result.cross_validation["cv_r2_mean"] >= 0.0  # Clip à 0


def test_cv_deterministic_same_seed():
    """CV avec seed fixe → résultats reproductibles."""
    np.random.seed(42)
    df = pd.DataFrame({
        "Budget": np.random.uniform(0, 1000, 50),
        "CA": np.random.normal(5000, 1000, 50),
    })
    sim_config = SimulationConfig(target="CA", feature="Budget", change_pct=0.10)
    
    result1 = simulate_scenario(df, target=sim_config.target, feature=sim_config.feature, change_pct=sim_config.change_pct)
    result2 = simulate_scenario(df, target=sim_config.target, feature=sim_config.feature, change_pct=sim_config.change_pct)
    
    if result1.cross_validation is not None and result2.cross_validation is not None:
        assert result1.cross_validation["cv_r2_mean"] == result2.cross_validation["cv_r2_mean"]
