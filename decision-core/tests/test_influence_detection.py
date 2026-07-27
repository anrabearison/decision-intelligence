"""
Tests du module de détection de points influents (distance de Cook).

Contexte (voir README) : la corrélation de Pearson et la régression
linéaire sont sensibles aux points influents, y compris des points
individuellement plausibles (pas des anomalies univariées détectables
par IQR) mais dont la combinaison est incohérente avec la relation
entre les deux variables. La distance de Cook détecte ce cas, contrairement
à detect_anomalies_iqr qui ne regarde qu'une colonne à la fois - vérifié
empiriquement avant l'implémentation (cf. commit).
"""
import numpy as np
import pandas as pd
import pytest
from decision_core.influence_detection import detect_influential_points


def _linear_dataset_with_bivariate_trap():
    """29 points sur une vraie droite Y=2X+bruit, + 1 point piège :
    X et Y individuellement dans la plage normale, mais incohérents
    entre eux (X=15 -> Y attendu ~30, mais Y=55 fourni)."""
    np.random.seed(11)
    n = 29
    X = np.random.uniform(10, 30, n)
    Y = 2 * X + np.random.normal(0, 3, n)
    X = np.append(X, 15)
    Y = np.append(Y, 55)
    return pd.DataFrame({"X": X, "Y": Y})


def _linear_dataset_with_extreme_outlier():
    """29 points de bruit sans relation, + 1 point extrême univarié
    (X=100000, Y=0.001)."""
    np.random.seed(5)
    X = list(range(1, 30))
    Y = list(np.random.normal(50, 5, 29))
    X.append(100000)
    Y.append(0.001)
    return pd.DataFrame({"X": X, "Y": Y})


class TestDetectsBivariateInfluentialPoint:
    def test_flags_the_trap_point(self):
        df = _linear_dataset_with_bivariate_trap()
        result = detect_influential_points(df, feature="X", target="Y")
        assert 29 in result["indices"]

    def test_trap_point_has_highest_distance(self):
        df = _linear_dataset_with_bivariate_trap()
        result = detect_influential_points(df, feature="X", target="Y")
        assert result["max_distance_index"] == 29

    def test_iqr_alone_would_have_missed_this_point(self):
        # non-régression du raisonnement qui a motivé ce module :
        # confirme qu'IQR univarié ne suffit pas (documenté, pas juste affirmé)
        from decision_core.anomaly_detection import detect_anomalies_iqr
        df = _linear_dataset_with_bivariate_trap()
        iqr_x = detect_anomalies_iqr(df["X"])
        iqr_y = detect_anomalies_iqr(df["Y"])
        assert 29 not in iqr_x["indices"]
        assert 29 not in iqr_y["indices"]


class TestDetectsExtremeUnivariateOutlier:
    def test_flags_the_extreme_point_too(self):
        df = _linear_dataset_with_extreme_outlier()
        result = detect_influential_points(df, feature="X", target="Y")
        assert 29 in result["indices"]


class TestNoFalsePositivesOnCleanData:
    def test_few_or_no_influential_points_on_well_behaved_linear_data(self):
        # Le seuil 4/n est une heuristique avec un taux de faux positifs
        # connu (~5-10%) même sur des données propres - on vérifie donc
        # qu'une large majorité des points ne sont PAS signalés, pas un
        # zéro absolu qui serait une attente statistiquement irréaliste.
        np.random.seed(42)
        n = 40
        X = np.random.uniform(0, 100, n)
        Y = 3 * X + np.random.normal(0, 5, n)
        df = pd.DataFrame({"X": X, "Y": Y})
        result = detect_influential_points(df, feature="X", target="Y")
        assert len(result["indices"]) <= n * 0.15


class TestResultStructure:
    def test_includes_threshold_and_n(self):
        df = _linear_dataset_with_bivariate_trap()
        result = detect_influential_points(df, feature="X", target="Y")
        assert result["threshold"] == pytest.approx(4 / 30, abs=0.001)
        assert result["n"] == 30
