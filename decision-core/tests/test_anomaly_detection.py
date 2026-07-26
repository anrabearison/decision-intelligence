"""
Tests du module de détection d'anomalies (méthode IQR).
Limite documentée : peu fiable sous ~30 lignes (README).
"""
import pandas as pd
import pytest
from decision_core.anomaly_detection import detect_anomalies_iqr


class TestAnomalyDetectionClearOutlier:
    def test_detects_obvious_outlier(self):
        # 9 valeurs "normales" autour de 100 + un outlier evident à 900
        series = pd.Series([98, 101, 99, 102, 100, 97, 103, 100, 101, 900])
        result = detect_anomalies_iqr(series)
        assert 9 in result["indices"]  # index du 900

    def test_no_outlier_on_uniform_data(self):
        series = pd.Series([10, 11, 10, 12, 11, 10, 11, 12, 10, 11])
        result = detect_anomalies_iqr(series)
        assert result["indices"] == []


class TestAnomalyDetectionSmallSampleWarning:
    def test_flags_small_sample_as_unreliable(self):
        df = pd.read_csv(
            __file__.replace("test_anomaly_detection.py", "fixtures/troupeau_test.csv")
        )
        result = detect_anomalies_iqr(df["Temperature"])
        assert result["reliable"] is False
        assert result["n"] == 10

    def test_large_enough_sample_is_reliable(self):
        series = pd.Series(list(range(50)))
        result = detect_anomalies_iqr(series)
        assert result["reliable"] is True


class TestAnomalyDetectionOnNonNumeric:
    def test_raises_on_non_numeric_series(self):
        series = pd.Series(["a", "b", "c"])
        with pytest.raises(TypeError):
            detect_anomalies_iqr(series)
