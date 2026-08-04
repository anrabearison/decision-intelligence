"""Tests unitaires pour la détection de distributions non-gaussiennes."""
import pandas as pd
import numpy as np
import pytest
from decision_core.stats.distribution import (
    detect_count_data_distribution,
    detect_zero_inflation,
    detect_heavy_tail,
)


class TestDistributionDetectors:
    def test_detects_count_data_for_small_integer_counts(self):
        df = pd.DataFrame({"Count": [0, 1, 0, 2, 1, 3, 2, 1, 0, 2]})
        result = detect_count_data_distribution(df["Count"])
        assert result is not None
        assert result.feature == "Count"
        assert result.unique_values == 4
        assert result.zero_ratio == 0.3

    def test_rejects_non_integer_values_for_count_data(self):
        df = pd.DataFrame({"Count": [0.1, 1.2, 2.5, 3.7, 4.6, 5.8, 1.0, 0.0, 2.0, 3.0]})
        result = detect_count_data_distribution(df["Count"])
        assert result is None

    def test_rejects_large_count_mean_for_count_data(self):
        df = pd.DataFrame({"Count": [10, 12, 15, 8, 20, 25, 18, 22, 19, 11]})
        result = detect_count_data_distribution(df["Count"])
        assert result is None

    def test_detects_zero_inflation(self):
        df = pd.DataFrame({"Claims": [0, 0, 0, 1, 0, 2, 0, 0, 3, 0, 0, 4]})
        result = detect_zero_inflation(df["Claims"])
        assert result is not None
        assert pytest.approx(result.zero_ratio, rel=1e-3) == 2 / 3
        assert result.unique_values == 5

    def test_rejects_zero_inflation_for_low_zero_ratio(self):
        df = pd.DataFrame({"Claims": [0, 1, 0, 2, 1, 2, 3, 4, 0, 1]})
        result = detect_zero_inflation(df["Claims"])
        assert result is None

    def test_detects_heavy_tail_distribution(self):
        heavy = [1, 1, 2, 2, 3, 3, 2, 1, 1, 50, 100, 200]
        df = pd.DataFrame({"Loss": heavy})
        result = detect_heavy_tail(df["Loss"])
        assert result is not None
        assert result.skewness > 1.0
        assert result.kurtosis > 1.0

    def test_rejects_symmetric_distribution_for_heavy_tail(self):
        normal = np.random.normal(100, 10, 20)
        df = pd.DataFrame({"Normal": normal})
        result = detect_heavy_tail(df["Normal"])
        assert result is None

    def test_zero_inflated_count_data_still_reports_both(self):
        df = pd.DataFrame({"Loss": [0, 0, 1, 0, 2, 0, 3, 0, 0, 4, 0, 10]})
        count_result = detect_count_data_distribution(df["Loss"])
        zero_result = detect_zero_inflation(df["Loss"])
        assert count_result is not None
        assert zero_result is not None

    def test_detect_heavy_tail_requires_positive_median(self):
        df = pd.DataFrame({"Loss": [-100, -50, -20, -10, -5, 0, 5, 200, 300, 1000]})
        result = detect_heavy_tail(df["Loss"])
        assert result is None
