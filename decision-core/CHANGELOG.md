# Changelog

All notable changes to decision-core will be documented in this file.

## [Unreleased]

### Added (P0 - Régression logistique et causalité)

- **Régression logistique automatique** pour les cibles binaires (Churn, Panne, Guéri, etc.)
  - Ajout de `LogisticRegressionResult` dataclass
  - Ajout de `is_binary_target()` pour détecter les cibles binaires
  - Ajout de `fit_logistic_regression()` pour ajuster une régression logistique
  - Intégration automatique dans `fit_simple_regression()` avec basculement sur logistique
- **Avertissements de causalité**
  - Disclaimer systématique "Corrélation ≠ Causalité" dans `render_text_summary()`
  - Encadré jaune visible dans `render_html()` avec le même avertissement
- **Détection de facteurs confondants**
  - Ajout de `detect_confounders()` pour identifier les corrélations spurieuses
  - Intégration dans le reporting pour les 3 premières corrélations
  - Avertissement automatique quand un facteur confondant est détecté

### Added (P1.2 - Détection de non-linéarité)

- **Détection de patterns quadratiques**
  - Ajout de `detect_quadratic_pattern()` pour détecter les courbes en U et les optimaux gaussiens
  - Comparaison R² ajusté linéaire vs quadratique
  - Test de significativité du coefficient quadratique (p < 0.05)
  - Distinction automatique "u_curve" (creux) vs "optimum" (cloche)
- **Détection de patterns par paliers**
  - Ajout de `detect_step_pattern()` pour détecter les fonctions par paliers (step functions)
  - Discrétisation en quantiles adaptative à la taille de l'échantillon
  - Comparaison eta² par bins vs R² linéaire
  - Seuil d'amélioration de 0.05 pour éviter les faux positifs
- **Modèles de résultats**
  - Ajout de `QuadraticPatternResult` dataclass (frozen=True)
  - Ajout de `StepPatternResult` dataclass (frozen=True)
  - Export dans `decision_core.models.__init__`
- **Intégration dans le reporting**
  - Ajout de `_build_nonlinearity_warnings()` dans `reporting/warnings.py`
  - Détection limitée aux paires de top_correlations pour éviter l'explosion combinatoire
  - Avertissements pédagogiques en français pour chaque type de relation détectée
  - Avertissement spécifique dans `_build_simulation_warnings()` si la feature de simulation est non-linéaire
- **Garde-fous pour petit échantillon**
  - Seuil minimum n >= 10 pour toute détection de non-linéarité
  - Robustesse sur ~15 lignes (taille typique des datasets d'exemple)
- **Tests**
  - 10 tests unitaires dans `test_nonlinearity.py`
  - Tests pour courbes en U, optimaux, relations linéaires, paliers, et garde-fous
  - Test d'intégration avec `generate_report()`
  - Validation sur `energie_batiments_2025.csv` et `agriculture_rendement_2025.csv`
  - Couverture > 89% sur les nouveaux fichiers

### Added (P1.1 - Encodage catégoriel et sous-groupes)

- **Encodage one-hot automatique**
  - Ajout de `encode_categorical_features()` pour encoder les variables catégorielles
  - Paramètre `max_cardinality` (défaut 10) pour limiter l'encodage
  - Paramètre `encode_categorical=True` dans `fit_simple_regression()`
  - Préservation des colonnes numériques
- **Détection de sous-groupes significatifs**
  - Ajout de `detect_significant_subgroups()` utilisant eta-carré (η²)
  - Seuil par défaut η² = 0.14 (grand effet selon Cohen)
  - Retourne les moyennes par groupe pour interprétation
  - Intégration dans le reporting avec avertissements automatiques
- **Rapports segmentés**
  - Ajout de `generate_segmented_reports()` pour générer des rapports par sous-groupe
  - Paramètre `min_group_size` pour éviter les groupes trop petits
  - Supporte plusieurs colonnes de groupement

### Changed

- **Refactoring** : Création de sous-packages `io`, `quality`, `stats`, `simulation`
- **Backward compatibility** : Fichiers de compatibilité pour les imports existants
- **Tests** : 175 tests passants (95% de couverture)
- **Documentation** : Ajout de docstrings et exemples d'utilisation

### Fixed

- **Bug P0.1** : Correction de `detect_confounders()` - ajout de `index=df.index` pour éviter la perte d'alignement
- **Bug P0.2** : Correction de `fit_logistic_regression()` - remplacement de `minimize_scalar` par `minimize` multivarié avec L-BFGS-B
- **Bug P1.1** : Correction de la détection de sous-groupes dans le reporting - vérification que `numeric_cols` n'est pas vide

## [0.1.0] - Initial Release

### Added

- Régression linéaire simple et multivariée
- Détection d'anomalies via IQR
- Profiling des données (statistiques descriptives, corrélations)
- Simulation de scénarios
- Génération de rapports (texte et HTML)
- Détection d'influence (distance de Cook)
- Détection de colonnes dérivées
- Validation des données
- Détection de types automatique
