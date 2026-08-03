# Decision-Core

Moteur d'analyse de données pour la prise de décision, avec régression, détection d'anomalies, simulation et génération de rapports.

## Installation

```bash
pip install -e .
```

## Fonctionnalités principales

### Régression

- **Régression linéaire simple** : `fit_simple_regression(df, target, feature)`
- **Régression multivariée** : `fit_multivariate_regression(df, target, features)`
- **Régression logistique** (automatique pour cibles binaires) : `fit_logistic_regression(df, target, feature)`
- **Détection de facteurs confondants** : `detect_confounders(df, target, feature)`

### Traitement des variables catégorielles

- **Encodage one-hot automatique** : `encode_categorical_features(df, max_cardinality=10)`
- **Détection de sous-groupes significatifs** (eta-carré) : `detect_significant_subgroups(df, target, threshold_eta_squared=0.14)`
- **Rapports segmentés** : `generate_segmented_reports(df, group_by, generate_report_func, config)`

### Rapports et visualisation

- **Génération de rapports** : `generate_report(df, config)`
- **Rendu textuel** : `render_text_summary(report)`
- **Rendu HTML** : `render_html(report)`

### Autres fonctionnalités

- **Détection d'anomalies** : `detect_anomalies_iqr(df, k=1.5)`
- **Profiling des données** : `descriptive_stats(df)`, `correlation_matrix(df)`
- **Simulation de scénarios** : `simulate_scenario(df, target, feature, change_pct)`

## Nouveautés (P0 et P1.1)

### P0 : Régression logistique et avertissements de causalité

- **Régression logistique automatique** pour les cibles binaires (Churn, Panne, Guéri, etc.)
- **Détection automatique de cibles binaires** via `is_binary_target()`
- **Disclaimer systématique** "Corrélation ≠ Causalité" dans tous les rapports
- **Détection de facteurs confondants** pour identifier les corrélations spurieuses

### P1.1 : Encodage catégoriel et détection de sous-groupes

- **Encodage one-hot automatique** des variables catégorielles (cardinalité ≤ 10)
- **Détection de sous-groupes significatifs** via eta-carré (η²)
- **Paramètre `encode_categorical=True`** dans `fit_simple_regression()` pour activer l'encodage
- **Avertissements automatiques** dans les rapports quand un sous-groupe significatif est détecté

## Exemples d'utilisation

### Régression logistique pour cibles binaires

```python
from decision_core import import_file, fit_simple_regression

df = import_file("examples/saas_abonnements_2025.csv")

# La régression logistique est automatique pour les cibles binaires
model = fit_simple_regression(df, target="Desabonnement_Churn", feature="Utilisateurs_Actifs_Mensuels")

print(f"Type de modèle: {model.model_type}")  # logistic
print(f"Pseudo R²: {model.r_squared:.4f}")
print(f"Coefficient: {model.coefficient:.4f}")
```

### Encodage catégoriel

```python
from decision_core import encode_categorical_features, fit_simple_regression

df = import_file("examples/elevage_production_lait_2025.csv")

# Encodage one-hot des variables catégorielles
encoded_df = encode_categorical_features(df, max_cardinality=10)

# Régression avec encodage automatique
model = fit_simple_regression(df, target="Litres_Lait_Jour", feature="Poids_Kg", encode_categorical=True)
```

### Détection de sous-groupes

```python
from decision_core import detect_significant_subgroups

df = import_file("examples/elevage_production_lait_2025.csv")

# Détection des sous-groupes significatifs
subgroups = detect_significant_subgroups(df, "Litres_Lait_Jour")

for sg in subgroups:
    print(f"{sg['column']}: η² = {sg['eta_squared']:.4f}")
    print(f"Moyennes par groupe: {sg['group_means']}")
```

### Génération de rapport avec avertissements

```python
from decision_core import import_file, generate_report, render_text_summary
from decision_core.models import AnalysisConfig

df = import_file("examples/saas_abonnements_2025.csv")
config = AnalysisConfig(iqr_k=1.5)

report = generate_report(df, config)

# Le rapport inclut automatiquement :
# - Disclaimer "Corrélation ≠ Causalité"
# - Avertissements de facteurs confondants
# - Avertissements de sous-groupes significatifs

print(render_text_summary(report))
```

## Tests

```bash
pytest tests/ -v
```

## Structure du projet

```
decision_core/
├── __init__.py              # Point d'entrée principal
├── models/                  # Modèles de données
│   ├── regression.py        # Résultats de régression
│   ├── config.py            # Configurations
│   └── report.py            # Résultats de rapport
├── stats/                   # Fonctions statistiques
│   ├── regression.py        # Régression (linéaire, logistique)
│   ├── categorical.py       # Traitement catégoriel
│   ├── profiling.py         # Profiling des données
│   ├── influence_detection.py # Détection d'influence
│   └── derived_columns.py   # Détection de colonnes dérivées
├── quality/                 # Qualité des données
│   ├── validation.py        # Validation
│   ├── type_detection.py    # Détection de types
│   └── anomaly_detection.py # Détection d'anomalies
├── reporting/               # Génération de rapports
│   ├── builder.py          # Construction de rapports
│   ├── renderers.py        # Rendu (texte, HTML)
│   ├── scoring.py          # Scoring
│   └── warnings.py         # Génération de warnings
└── simulation/              # Simulation de scénarios
    └── scenario.py         # Scénarios
```

## Limites

- **Régression linéaire uniquement** (pas de choix utilisateur de modèle)
- **Pas de régression polynomiale** (P1.2 à venir)
- **Encodage one-hot uniquement** (pas de target encoding)
- **Seuil fixe pour eta-carré** (0.14 = grand effet selon Cohen)

## License

MIT
