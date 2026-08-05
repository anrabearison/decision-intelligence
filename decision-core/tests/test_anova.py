"""Tests unitaires pour ANOVA et détection d'eta-carré significatif."""
import numpy as np
import pandas as pd
import pytest
from decision_core.stats.anova import compute_eta_squared_with_significance, EtaSquaredResult


def test_compute_eta_squared_with_significance_returns_reliable_for_large_groups():
    y = np.array([1, 2, 1, 2, 10, 11, 10, 11])
    groups = pd.Series(['A', 'A', 'B', 'B', 'C', 'C', 'D', 'D'])

    result = compute_eta_squared_with_significance(y, groups, min_group_size=2)

    assert isinstance(result, EtaSquaredResult)
    assert result.reliable is True
    assert result.n == 8
    assert result.n_groups == 4
    assert result.eta_squared > 0
    assert 0 <= result.p_value <= 1
    assert result.f_statistic >= 0


def test_compute_eta_squared_with_significance_clamps_to_one_for_perfect_group_relation():
    y = np.array([1.0] * 5 + [2.0] * 5 + [3.0] * 5)
    groups = pd.Series(['A'] * 5 + ['B'] * 5 + ['C'] * 5)

    result = compute_eta_squared_with_significance(y, groups, min_group_size=2)

    assert result.reliable is True
    assert result.eta_squared == 1.0


def test_compute_eta_squared_with_significance_clamps_numeric_noise_from_real_example():
    import os
    from decision_core.importer import import_file

    examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples')
    df = import_file(os.path.join(examples_dir, 'ventes_magasin_2025.csv'))

    result = compute_eta_squared_with_significance(df['Prix_Unitaire'], df['Region'])

    assert result.eta_squared <= 1.0


def test_generate_report_for_ventes_magasin_region_warning_is_not_above_100_percent():
    import os
    from decision_core.importer import import_file
    from decision_core.report import generate_report

    examples_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'examples')
    df = import_file(os.path.join(examples_dir, 'ventes_magasin_2025.csv'))
    report = generate_report(df)

    region_warnings = [
        w for w in report['warnings']
        if 'Region' in w and 'explique' in w
    ]
    assert region_warnings
    for warning in region_warnings:
        percent_text = warning.split('explique ')[1].split('%')[0]
        assert float(percent_text) <= 100.0


def test_compute_eta_squared_with_significance_marks_small_groups_unreliable():
    y = np.array([1, 2, 3, 4, 5, 6])
    groups = pd.Series(['A', 'A', 'B', 'B', 'C', 'D'])

    result = compute_eta_squared_with_significance(y, groups, min_group_size=2)

    assert result.reliable is False
    assert result.p_value == 1.0
    assert result.f_statistic == 0.0


def test_detect_confounders_captures_u_pattern_confounder():
    df = pd.DataFrame({
        'target': [3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 3, 3],
        'feature': [100, 110, 90, 105, 10, 12, 8, 11, 10, 9, 11, 12, 100, 105, 95, 98],
        'confounder': ['A'] * 4 + ['B'] * 4 + ['C'] * 4 + ['D'] * 4,
        'noise': ['X', 'Y', 'X', 'Y'] * 4,
    })

    from decision_core.stats.regression import detect_confounders

    result = detect_confounders(df, target='target', feature='feature', threshold=0.05, min_group_size=2)

    assert 'confounder' in result
    assert 'noise' not in result
