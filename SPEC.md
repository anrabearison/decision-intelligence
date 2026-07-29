# Decision Intelligence Engine — Spécification technique

**Repo** : `github.com/anrabearison/decision-intelligence`
**Dernière mise à jour** : Phase 1a complète, Phase 2 en cours (frontend fonctionnel)
**Statut des tests** : 104 tests `decision-core`, 18 tests `decision-engine`, 0 test `frontend`

---

## 1. Vision et objectifs

L'objectif n'est pas de créer une application, mais un **moteur de décision** (Decision Core). L'interface web n'est qu'une façade ; le véritable produit est le moteur de calcul statistique, fiable et déterministe.

Trois objectifs guident le projet, avec des critères de succès distincts :

| Objectif | Ce qui compte | Ce qui ne compte pas |
|---|---|---|
| **Portfolio** (recrutement international) | Rigueur mathématique visible, code testé et documenté | Produit fini, UI soignée |
| **Usage personnel / entourage** | Aide réelle à la décision, rapidité | Robustesse, scalabilité |
| **SaaS** (potentiel, non engagé) | Marché validé, simplicité pour un non-matheux | Sophistication excessive |

### Pourquoi pas simplement un chat IA générique ?

Pour une analyse ponctuelle sur un petit jeu de données, un chat IA générique (Claude, etc.) suffit très bien. Un moteur dédié apporte une valeur différente : fiabilité du calcul (déterministe, pas génératif), absence de limite de contexte, reproductibilité/auditabilité, automatisation via API, coût à l'échelle. Cible : les utilisateurs qui n'ont ni le temps ni l'envie de développer une compétence de prompting, ou qui ont besoin de résultats reproductibles pour des raisons professionnelles — pas l'utilisateur déjà expert en IA générative.

---

## 2. Roadmap

| Phase | Contenu | Statut |
|---|---|---|
| 0 — Foundation | Architecture, standards, conventions | ✅ |
| 1a — Decision Core Foundation | Import, validation, profiling, simulation simple, rapport | ✅ Complète |
| 1a.5 — Validation légère | Rapport montré à 5-10 personnes cibles | ⏳ Non réalisée |
| 1b — Decision Core Analytics | Monte Carlo, distributions, sensibilité | ⏳ Non commencée |
| 2 — Decision Studio | Interface React + façade FastAPI | 🚧 Frontend fonctionnel, pas de tests automatisés |
| 3 — Decision Intelligence | Prédiction, risque, recommandation | ⏳ Non commencée |
| 4 — AI Layer | LLM Gateway, explications, chat, RAG | ⏳ Non commencée |
| 4.5 — Market Validation | Tests utilisateurs approfondis | ⏳ Non réalisée |
| 5 — Decision Cloud | NestJS, auth, organisations, facturation, Supabase | ⏳ Non commencée |
| 6 — Decision Ecosystem | Marketplace, connecteurs, SDK, API publique | ⏳ Non commencée |

---

## 3. Architecture

### 3.1 État actuel (Phase 2)

```
React (frontend) ──HTTP──▶ FastAPI (decision-engine) ──import──▶ decision-core (package Python)
```

`decision-engine` est une façade fine : reçoit un fichier, appelle `decision-core`, retourne du JSON. Aucune logique métier, aucune notion d'utilisateur, pas de base de données.

### 3.2 Cible (Phase 5+)

```
React ──▶ NestJS (auth, orgs, facturation) ──HTTP interne──▶ FastAPI (decision-engine) ──▶ decision-core
                    │
              Supabase (PostgreSQL + Storage)
```

`decision-core` reste strictement identique et agnostique de l'utilisateur, qu'il soit appelé directement (Phase 2) ou via NestJS (Phase 5+) — c'est le bénéfice de la séparation stricte adoptée dès le départ.

### 3.3 Décisions techniques actées

| Décision | Alternative écartée | Raison |
|---|---|---|
| FastAPI seul pour l'instant | NestJS dès maintenant | Pas d'utilisateurs à gérer avant Phase 5 ; complexité prématurée |
| React + Vite | Next.js fusionnant frontend/backend | Découplage préservé pour API publique/mobile future |
| `decision-core` = package Python autonome | Logique dans `decision-engine` | Testable isolément, réutilisable (CLI, notebook) |
| Monorepo, 1 seul repo Git | Multi-repo | Solo dev, historique cohérent pour portfolio |
| Railway/Render au déploiement | Docker Compose partout | `docker-compose.yml` réservé au développement local |
| Supabase pour la BDD (Phase 5+) | PostgreSQL auto-hébergé | Budget 0€, plan gratuit suffisant à l'échelle actuelle |

---

## 4. `decision-core` — spécification des modules

Package Python installable (`pip install -e .`), zéro dépendance à FastAPI/NestJS/HTTP.

### 4.1 `importer.py`

```python
import_file(path: str) -> pd.DataFrame
```
- Formats acceptés : CSV, Excel (`.xlsx`, `.xls`, première feuille uniquement)
- **Ingestion locale-aware** (ajouté après audit) :
  - Fallback d'encodage déterministe : UTF-8 → CP1252 (Windows)
  - Détection de délimiteur avec **vérification de cohérence** (nombre de champs par ligne) — refuse explicitement un fichier ambigu plutôt que deviner (empêche la corruption silencieuse de colonnes)
  - `FRENCH_NA_VALUES` : reconnaît `N/D`, `ND`, `N/C`, `NC`, `NR`, `Non renseigné`, `n.d.` en plus de la liste pandas par défaut
  - Normalisation automatique de la virgule décimale française (`"12,50"` → `12.50`) si ≥90% des valeurs non nulles d'une colonne texte deviennent des flottants valides après normalisation
- Exceptions : `UnsupportedFileFormatError`, `FileNotFoundError`, et des sous-classes de `ValueError`/`pandas.errors.*` pour les fichiers corrompus/vides/malformés

### 4.2 `validation.py`

```python
validate_dataset(df: pd.DataFrame) -> dict
# {n_rows, n_columns, duplicates_count, missing_values: {col: count}}
```
Signale uniquement — ne corrige jamais automatiquement les données (principe appliqué dans tout le projet).

### 4.3 `type_detection.py`

```python
detect_column_type(series: pd.Series) -> str
# "numeric_continuous" | "numeric_discrete" | "categorical" |
# "boolean" | "datetime" | "identifier" | "text_free" | "unknown"
```
Heuristique documentée comme imparfaite (ex. un prix en valeurs entières est classé `numeric_discrete`, pas `numeric_continuous`).

### 4.4 `profiling.py`

```python
descriptive_stats(series: pd.Series) -> dict
# {mean, std_dev, min, max, median}

legitimate_numeric_columns(df: pd.DataFrame) -> list
# Exclut les identifiants numériques séquentiels (détection via
# corrélation quasi parfaite avec l'ordre des lignes, seuil 0.999)

correlation_matrix(df: pd.DataFrame) -> pd.DataFrame
correlation_pvalues(df: pd.DataFrame) -> list
# [{column_a, column_b, value, p_value, p_value_adjusted,
#   significant_after_correction}]
# Correction Benjamini-Hochberg (FDR) pour comparaisons multiples.
# Plafonné à MAX_COLUMNS_FOR_CORRELATION=50 colonnes (raison de
# performance, croissance quadratique C(k,2)).
```

### 4.5 `anomaly_detection.py`

```python
detect_anomalies_iqr(series: pd.Series, k: float = 1.5) -> dict
# {indices, lower_bound, upper_bound, n, reliable}
```
Méthode IQR (Tukey, 1977). `reliable=False` si `n < MIN_RELIABLE_SAMPLE_SIZE (30)`. Limite documentée : ne détecte que les anomalies univariées, jamais les points bivariablement incohérents (cf. `influence_detection.py`).

### 4.6 `regression.py`

```python
fit_simple_regression(df, target: str, feature: str) -> dict
# {slope, intercept, r_squared, feature, target}

fit_multivariate_regression(df, target: str, features: list) -> dict
# {intercept, coefficients, r_squared, target,
#  condition_number, multicollinearity_warning}
```
- `InsufficientDataError(ValueError)` : levée si <3 lignes valides après `dropna()` locale, ou variance nulle sur une variable — garde-fou centralisé (`_validate_regression_inputs`), réutilisé par `influence_detection.py` pour éviter la duplication de logique.
- `multicollinearity_warning=True` si le nombre de conditionnement (calculé sur features **standardisées**, pour isoler la vraie colinéarité des différences d'échelle) dépasse 30 (Belsley, Kuh & Welsch, 1980).

### 4.7 `influence_detection.py`

```python
compute_cooks_distance(df, feature, target) -> np.ndarray
detect_influential_points(df, feature, target, threshold_ratio=4.0) -> dict
# {indices, n, threshold, max_distance, max_distance_index}
```
Distance de Cook — complète `detect_anomalies_iqr` : détecte les points individuellement plausibles mais bivariablement incohérents avec la relation entre deux variables (invisibles à l'IQR univarié, vérifié empiriquement). Retourne 0 partout si l'ajustement est parfait (MSE≈0, évite une division 0/0).

### 4.8 `simulation.py`

```python
simulate_scenario(df, target, feature, change_pct: float) -> dict
# {baseline, simulated, change_pct, change_pct_reliable,
#  model_r_squared, feature, target}
```
Projection déterministe via régression linéaire simple (pas de Monte Carlo — prévu Phase 1b). `change_pct=None` et `change_pct_reliable=False` si le baseline est proche de zéro relativement à l'écart-type de la cible (évite un pourcentage trompeur type "+256%").

### 4.9 `report.py`

```python
generate_report(df, simulation_config: dict | None = None) -> dict
# {dataset_summary, validation, profiling, top_correlations,
#  warnings, simulation?}

render_text_summary(report: dict) -> str
render_html(report: dict) -> str  # échappement HTML systématique (anti-XSS)
```
Orchestre tous les modules ci-dessus. Génère des avertissements contextuels : échantillon petit (global et par simulation), R² faible, points influents, comparaisons multiples, troncature de colonnes, échec de normalisation.

---

## 5. `decision-engine` — spécification API

FastAPI, façade fine sur `decision-core`.

### `GET /health`
`{"status": "ok"}`

### `POST /engine/analyze`
**Requête** (`multipart/form-data`) :
| Champ | Type | Requis |
|---|---|---|
| `file` | fichier CSV/Excel | oui |
| `target` | string | non (active la simulation si fourni avec `feature`) |
| `feature` | string | non |
| `change_pct` | float | non |

**Réponse 200** : le dict `report` de `generate_report` (JSON)
**Réponse 400** : `{"detail": "..."}` — toute erreur imputable aux données (`ValueError`, `TypeError`, `KeyError`, `UnsupportedFileFormatError` et leurs sous-classes)
**Réponse 413** : fichier > 50 Mo
**Réponse 500** : erreur imprévue uniquement, message générique sans détails internes, journalisée côté serveur

### Sécurité
- Middleware de clé interne (`X-Internal-Key` vs `INTERNAL_API_KEY`) — inactif si la variable d'environnement n'est pas définie (cas Phase 2, service public), actif en Phase 5 (service interne derrière NestJS)
- Gestion d'erreur par **classes de base** (`ValueError`, `TypeError`, `KeyError`, `UnsupportedFileFormatError`) plutôt qu'une liste d'exceptions spécifiques — un audit a montré que 5 des 8 exceptions atteignables n'étaient pas couvertes par l'approche liste blanche
- Filet de sécurité générique (`Exception` → 500) pour tout bug non anticipé, jamais de stack trace exposée au client

---

## 6. Frontend — spécification

React 18 + Vite, un seul écran (pas de routing).

**Flux** : `UploadZone` (drag & drop / clic) → `ScanConsole` (animation pendant l'appel API) → `ReportView` (résumé, avertissements, corrélations en barres colorées, résultat de simulation).

**Client API** centralisé (`src/api/client.js`) — un seul point de changement le jour où NestJS s'insère entre le frontend et `decision-engine`.

**Gap connu** : aucune suite de tests automatisés. Un bug (`change_pct: null` non géré, crash `TypeError`) a atteint la production de code avant d'être détecté manuellement, précisément à cause de cette absence — noté explicitement comme dette technique.

---

## 7. Modèle de données (fixtures de référence)

| Fixture | Lignes | Cas testé |
|---|---|---|
| `ventes_test.csv` | 10 | Cas retail de base |
| `troupeau_test.csv` | 10 | Domaine élevage |
| `tresorerie_test.csv` | 10 | Domaine finance |
| `dataset_avec_problemes.csv` | 6 | Doublons, valeurs manquantes |
| `education_45.csv` | 45 | Signal modéré (R²≈0.35) |
| `controle_qualite_35.csv` | 35 | Identifiant numérique séquentiel (piège) |
| `petit_commerce_40j.csv` | 40 | Rendement décroissant (marketing) |
| `immobilier_50.csv` | 50 | Signal fort et propre (R²≈0.99) |
| `bruit_pur_40.csv` | 40 | Aucun signal réel (R²≈0.06) |
| `rh_avec_doublons_39.csv` | 39 | Doublons + NaN réels combinés |

---

## 8. Stratégie de test

TDD strict sur tout `decision-core`/`decision-engine` : tests écrits avant le code, rouge confirmé avant chaque implémentation, suite complète relancée après chaque changement (pas seulement le module modifié).

```bash
cd decision-core && pip install -e . && pytest tests/ -v
cd decision-engine && pip install -e ../decision-core -r requirements.txt && pytest tests/ -v
```

104 + 18 = 122 tests, structurés en classes par cas (`TestX`, une méthode = un scénario).

---

## 9. Limites connues (Phase 1a)

Volontaires, chacune correspond à une fonctionnalité repoussée à une phase ultérieure :

- CSV/Excel uniquement, une seule table, une seule feuille Excel
- Fiable jusqu'à quelques centaines de milliers de lignes ; **calcul de corrélations plafonné à 50 colonnes** pour rester sous les timeouts HTTP
- Détection de type heuristique, imparfaite sur des cas limites documentés
- Aucune correction automatique des données (signalement uniquement)
- Détection d'anomalies peu fiable sous 30 lignes
- Régression linéaire uniquement (pas de sélection automatique de modèle — Phase 3)
- Corrélation ≠ causalité, rappelé explicitement à chaque rapport

---

## 10. Historique des audits et corrections

Trois séries d'audits structurés ont été menées, révélant et corrigeant les problèmes suivants (par ordre de découverte) :

1. **Identifiants numériques dans les corrélations** — un numéro de lot séquentiel apparaissait comme corrélé à d'autres variables (artefact d'ordre des lignes)
2. **NaN silencieux en régression** — valeurs manquantes non filtrées avant `scipy`/`numpy`, résultats `NaN` sans erreur
3. **Pourcentage trompeur** — `change_pct` calculé même quand le baseline est proche de zéro (ex. `+256%` sur un signal quasi nul)
4. **Erreurs brutes non interceptées** — variance nulle, colonnes inexistantes, fichiers corrompus remontant en 500 avec stack trace
5. **XSS potentiel** — noms de colonnes non échappés dans le rendu HTML
6. **Duplication de logique** — `influence_detection.py` avait réintroduit les bugs NaN/variance déjà corrigés ailleurs, faute de réutiliser le garde-fou commun
7. **Corruption silencieuse de colonnes** — virgule décimale française dans un fichier délimité par virgule, sans échappement (le bug le plus grave trouvé : aucune erreur, données visiblement normales mais fausses)
8. **Comparaisons multiples** — `top_correlations` signalait une corrélation "forte" par pur hasard dans 97% des cas à 15 colonnes/n=30, sans correction statistique
9. **Multicolinéarité non détectée** — coefficients de régression multivariée numériquement valides mais statistiquement absurdes sur des variables quasi-colinéaires
10. **Performance quadratique** — 200 colonnes = 34s de calcul, incompatible avec un traitement HTTP synchrone

Chaque correction a suivi le cycle TDD (test rouge reproduisant le bug → fix → suite complète relancée), documenté en détail dans les messages de commit correspondants.

---

## 11. Sécurité

- Clé API interne (NestJS ↔ FastAPI, Phase 5+) : générée via `openssl rand -hex 32`, jamais commitée, stockée en variables d'environnement des deux services
- Plan de réponse en cas de fuite : régénération immédiate, mise à jour synchrone des deux services, redéploiement simultané
- `decision-engine` jamais exposé publiquement une fois NestJS en place — isolation réseau comme protection principale, la clé API comme défense supplémentaire
- Échappement HTML systématique dans `render_html` (le JSON API n'est jamais échappé, React s'en charge côté frontend)

---

## 12. Déploiement (cible)

| Service | Plateforme | Notes |
|---|---|---|
| Frontend (React) | Vercel / Netlify | Preview deployments automatiques par PR |
| `decision-engine` (FastAPI) | Railway / Render | Root directory = `decision-engine/` |
| `backend` (NestJS, Phase 5+) | Railway / Render | Root directory = `backend/` |
| Base de données | Supabase (plan gratuit) | 500 Mo BDD, 1 Go Storage, pause après 7j d'inactivité |

`docker-compose.yml` réservé au développement local (tous les services + PostgreSQL ensemble), jamais utilisé en production sur ces plateformes.

---

## 13. Conventions de développement

- **Commits** : `type(scope): description` (Conventional Commits) — `feat`, `fix`, `test`, `docs`, `chore`
- **Nommage** : identifiants de code (variables, fonctions, classes) en anglais ; docstrings, commentaires et messages utilisateur en français
- **TDD non négociable** sur `decision-core`/`decision-engine` : aucun code métier écrit sans test rouge préalable
