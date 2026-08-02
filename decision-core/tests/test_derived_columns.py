"""
Tests du module de détection de colonnes dérivées.

Contexte (trouvé en test de lisibilité simulé) : une colonne calculée
à partir d'autres colonnes du même fichier (ex: Total = Prix * Quantité)
produit mécaniquement une corrélation très forte avec ses composantes -
ce n'est pas un insight, c'est une tautologie mathématique. Le rapport
présentait cette corrélation comme "la plus forte" sans aucune nuance,
alors qu'elle n'apprend rien de nouveau à l'utilisateur.
"""
import numpy as np
import pandas as pd
import pytest
from decision_core.derived_columns import detect_derived_relationships


class TestDetectsProductRelationship:
    def test_flags_total_as_product_of_price_and_quantity(self):
        rng = np.random.default_rng(0)
        prix = rng.uniform(10, 100, 40)
        quantite = rng.integers(1, 20, 40)
        total = prix * quantite
        df = pd.DataFrame({"Prix": prix, "Quantite": quantite, "Total": total})
        relationships = detect_derived_relationships(df, ["Prix", "Quantite", "Total"])
        assert frozenset(["Prix", "Total"]) in relationships
        assert frozenset(["Quantite", "Total"]) in relationships

    def test_does_not_flag_unrelated_columns(self):
        rng = np.random.default_rng(1)
        df = pd.DataFrame({
            "A": rng.normal(0, 1, 40),
            "B": rng.normal(0, 1, 40),
            "C": rng.normal(0, 1, 40),
        })
        relationships = detect_derived_relationships(df, ["A", "B", "C"])
        assert relationships == set()


class TestDetectsSumAndDifferenceRelationships:
    def test_flags_total_as_sum_of_two_columns(self):
        rng = np.random.default_rng(2)
        a = rng.uniform(10, 100, 40)
        b = rng.uniform(10, 100, 40)
        total = a + b
        df = pd.DataFrame({"A": a, "B": b, "Total": total})
        relationships = detect_derived_relationships(df, ["A", "B", "Total"])
        assert frozenset(["A", "Total"]) in relationships
        assert frozenset(["B", "Total"]) in relationships

    def test_flags_profit_as_difference_of_revenue_and_cost(self):
        rng = np.random.default_rng(3)
        revenu = rng.uniform(1000, 5000, 40)
        cout = rng.uniform(500, 2000, 40)
        profit = revenu - cout
        df = pd.DataFrame({"Revenu": revenu, "Cout": cout, "Profit": profit})
        relationships = detect_derived_relationships(df, ["Revenu", "Cout", "Profit"])
        assert frozenset(["Revenu", "Profit"]) in relationships
        assert frozenset(["Cout", "Profit"]) in relationships


class TestTolerance:
    def test_tolerates_small_rounding_noise(self):
        # Cas réaliste : arrondis lors de la saisie, la relation n'est
        # pas parfaitement exacte au centime près mais reste dérivée.
        rng = np.random.default_rng(4)
        prix = rng.uniform(10, 100, 40)
        quantite = rng.integers(1, 20, 40)
        total = np.round(prix * quantite) + rng.normal(0, 0.001, 40)
        df = pd.DataFrame({"Prix": prix, "Quantite": quantite, "Total": total})
        relationships = detect_derived_relationships(df, ["Prix", "Quantite", "Total"])
        assert frozenset(["Prix", "Total"]) in relationships

    def test_does_not_flag_genuinely_different_but_correlated_columns(self):
        # Deux colonnes corrélées mais PAS dérivées l'une de l'autre par
        # une formule exacte - une vraie relation statistique doit rester
        # un insight, pas être supprimée à tort par ce filtre.
        rng = np.random.default_rng(5)
        x = rng.uniform(10, 100, 40)
        y = 2 * x + rng.normal(0, 15, 40)  # relation bruitée, pas exacte
        df = pd.DataFrame({"X": x, "Y": y})
        relationships = detect_derived_relationships(df, ["X", "Y"])
        assert relationships == set()


class TestPerformance:
    def test_completes_quickly_on_50_columns(self):
        import time
        rng = np.random.default_rng(6)
        df = pd.DataFrame({f"V{i}": rng.normal(0, 1, 40) for i in range(50)})
        start = time.time()
        detect_derived_relationships(df, list(df.columns))
        elapsed = time.time() - start
        assert elapsed < 5.0


class TestHandlesMissingValues:
    def test_still_detects_relationship_with_a_few_nan_values(self):
        # Bug réel trouvé sur des données réalistes (persona "Rina") :
        # 1 NaN dans Quantité et 1 NaN dans Total sur 36 lignes suffisait
        # à faire passer le taux de correspondance sous le seuil de 95%,
        # car une comparaison impliquant NaN vaut toujours False -
        # chaque ligne avec NaN comptait à tort comme "ne correspond pas"
        # plutôt que d'être simplement exclue de la vérification.
        rng = np.random.default_rng(0)
        n = 36
        prix = rng.uniform(10, 100, n)
        quantite = rng.integers(1, 20, n).astype(float)
        total = prix * quantite
        quantite[3] = np.nan
        total[17] = np.nan
        df = pd.DataFrame({"Prix": prix, "Quantite": quantite, "Total": total})
        relationships = detect_derived_relationships(df, ["Prix", "Quantite", "Total"])
        assert frozenset(["Prix", "Total"]) in relationships
