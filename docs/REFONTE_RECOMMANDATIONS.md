# Recommandations pour la Refonte de decision-core
## Analyse stratégique issue des 18 tests inter-domaines

**Basé sur** : `docs/RAPPORT_TESTS_DOMAINES.md` (18 domaines testés)  
**Date** : Août 2026  
**Statut** : Document de décision — aucune modification du code n'est engagée

---

## 1. Réponse directe : Est-ce réalisable ?

**Oui, une refonte est réalisable — à condition de choisir le bon niveau.**

L'architecture actuelle du projet est saine. Les modules (`importer.py`, `profiling.py`,
`regression.py`, `simulation.py`, `report.py`, `anomaly_detection.py`) sont bien découpés
et indépendants. Il n'est pas nécessaire de tout réécrire. La question est de savoir
**quels modules faire évoluer, dans quel ordre, et jusqu'où**.

---

## 2. Ce que les recommandations actuelles couvrent

Les 4 recommandations de la section 6 du rapport et les 5 failles structurelles
de la section 5 couvrent ensemble environ **74% des critiques identifiées**.

| Critique (issue des 18 tests) | Tests concernés | Couverte ? |
|---|---|---|
| Variables texte / catégorielles ignorées | #1 #3 #5 #8 #10 #11 #14 #16 #18 | ✅ Oui — Faille F1 / Rec. 1 |
| Inversion de causalité par facteur confondant | #3 #6 #10 #17 | ✅ Partiellement — F2 (warnings) |
| Baseline = moyenne globale sans sens | #1 #11 #16 | ✅ Oui — Rec. 4 / F3 |
| Projection hors bornes (note > 20) | #7 | ✅ Oui — Rec. 3 |
| Courbe en U non captée | #13 #18 | ✅ Oui — F4 (polynomiale deg. 2) |
| Cible binaire (Churn) via régression linéaire | #15 | ✅ Oui — Rec. 2 |
| Distribution Zéro-Inflated (Assurance) | #12 | ✅ Oui — F5 |
| Comptages discrets (Poisson) | #9 | ✅ Oui — F5 |

---

## 3. Ce que les recommandations actuelles NE couvrent PAS

Ces critiques sont **réelles, prouvées par les tests, mais non adressées** par les
recommandations existantes. Elles représentent les 26% restants.

### 3.1 — Faux positifs de l'algorithme IQR sur les valeurs métier normales *(Test #1)*

**Le problème :** Les remises promotionnelles de 5% et 10% sont qualifiées d'anomalies
IQR car la médiane des remises est 0. Pour un commerçant, une promotion n'est pas
une erreur de saisie.

**Ce qu'il faudrait :** Un seuil configurable dans `anomaly_detection.py`, ou la
possibilité de marquer des colonnes comme "non soumises à détection d'anomalie".

**Complexité :** Faible. Changement localisé dans `anomaly_detection.py`.

---

### 3.2 — Tarification par paliers / fonctions en escalier *(Test #5 Logistique, Test #2 RH)*

**Le problème :** Les frais de port par tranches de poids (0-5 kg = 4,90 €, 5-10 kg = 7,90 €)
et les grilles salariales par ancienneté obéissent à des **fonctions discontinues en escalier**.
Ni une droite linéaire ni une parabole (polynomiale degré 2) ne peuvent les modéliser.

**Ce qu'il faudrait :** Une détection de segmentation par seuils (*changepoint detection* ou
*segmented regression*). Ce n'est pas dans les recommandations actuelles.

**Complexité :** Élevée. Représente un domaine statistique distinct. À traiter comme un
sprint séparé ou à signaler par un warning explicite dans le rapport généré.

---

### 3.3 — Biais de variable omise généralisé *(Test #4 Finance)*

**Le problème :** Quand un flux d'investissement exceptionnel (-25 000 €) est attribué
au seul délai de paiement, c'est un **biais de variable omise** : la variable `Type_Flux`
(texte : exploitation vs investissement) est absente du modèle. Le résultat est une
surestimation de +69%.

**La différence avec F1 :** Supporter les variables catégorielles (F1) résoudrait partiellement
ce cas — mais pas entièrement, car le problème est aussi l'absence d'analyse de
multicolinéarité entre les features explicatives elles-mêmes.

**Ce qu'il faudrait :** En plus de F1, une analyse de **variance partielle** (contrôle
des covariables) ou un warning explicite quand une variable catégorielle présente une
forte corrélation avec une variable numérique déjà dans le modèle.

**Complexité :** Moyenne à élevée.

---

### 3.4 — Inversion de causalité par saisonnalité temporelle *(Test #17 Tourisme)*

**Le problème :** Le moteur conclut qu'une baisse de prix de 10% ferait chuter les
visiteurs de 39%. En réalité, le musée augmente ses prix en été, quand il y a déjà
plus de visiteurs. La saisonnalité explique les deux variables simultanément.

**La différence avec F2 :** Un warning de causalité (F2) peut alerter l'utilisateur
mais ne peut pas **résoudre** le problème. La vraie solution nécessite soit :
- De la modélisation de séries temporelles (décomposition saisonnière, SARIMA)
- Du raisonnement causal explicite (graphes causaux / DAG)

Ces deux approches sont des domaines entiers qui dépassent le Niveau 1 de refonte.

**Recommandation réaliste :** Ajouter un warning contextuel dans `report.py` quand
une variable temporelle est détectée dans le dataset et que les corrélations sont fortes.
Ne pas prétendre résoudre le problème statistiquement.

**Complexité :** Très élevée pour la solution complète. Faible pour le warning.

---

### 3.5 — Distribution Pareto extrême *(Test #16 Cybersécurité)*

**Le problème :** 3 incidents critiques représentent 95% des coûts totaux. Le moteur
produit une baseline à 167 993 € qui ne correspond à aucune catégorie d'incident réelle.

**Couverture partielle :** F5 adresse les distributions non-gaussiennes (Poisson,
Zéro-Inflated), mais la loi de puissance (Pareto) est plus complexe et n'est pas
explicitement couverte par les recommandations actuelles.

**Ce qu'il faudrait :** Détecter les distributions fortement asymétriques (skewness > 2)
et recommander une transformation logarithmique ou un modèle log-normal avant la
régression. Un warning suffisamment explicite dans `report.py` constituerait déjà
une amélioration significative.

**Complexité :** Moyenne.

---

## 4. Tableau de couverture finale

| # | Critique | Tests | Couvert par les recs. actuelles | Couvert après F1-F5 complètes | Résidu |
|---|---|---|:---:|:---:|---|
| 1 | Variables catégorielles ignorées | #1 #3 #5 #8 #10 #11 #14 #16 #18 | ✅ | ✅ | — |
| 2 | Inversion de causalité | #3 #6 #10 #17 | ⚠️ | ⚠️ | Saisonnalité non résolue |
| 3 | Baseline naïve | #1 #11 #16 | ✅ | ✅ | — |
| 4 | Projection hors bornes | #7 | ✅ | ✅ | — |
| 5 | Courbe en U | #13 #18 | ✅ | ✅ | — |
| 6 | Cible binaire 0/1 | #15 | ✅ | ✅ | — |
| 7 | Zéro-Inflated | #12 | ✅ | ✅ | — |
| 8 | Comptages discrets (Poisson) | #9 | ✅ | ✅ | — |
| 9 | Faux positifs IQR | #1 | ❌ | ❌ | À adresser séparément |
| 10 | Tarification en escalier | #2 #5 | ❌ | ❌ | Complexité élevée |
| 11 | Biais de variable omise | #4 | ❌ | ⚠️ | F1 aide mais insuffisant |
| 12 | Saisonnalité temporelle | #17 | ❌ | ❌ | Hors scope Niveau 1 |
| 13 | Distribution Pareto | #16 | ❌ | ⚠️ | Warning possible, modèle non |

**Score de couverture :**
- Recommandations actuelles seules (4 items) : **~55%** des critiques résolues
- Recommandations actuelles + 5 failles (F1-F5) : **~74%** des critiques résolues
- Avec les 5 items supplémentaires de ce document : **~90%** des critiques résolues
- Les ~10% restants (saisonnalité, escalier complet) nécessitent un Niveau 2 de refonte

---

## 5. Recommandations opérationnelles classées par priorité

### 🔴 Priorité 1 — Impact immédiat, complexité faible à moyenne

#### R1. Support des variables catégorielles *(Faille F1 — 9/18 tests)*
**Module** : `importer.py`, `report.py`  
**Action** : Encoder les colonnes texte à faible cardinalité (< 20 valeurs uniques)
en variables indicatrices (*one-hot encoding*) et les inclure dans les corrélations.  
**Impact** : Résoudrait à lui seul le Paradoxe de Simpson (#3), l'effet Quartier (#8),
le Canal d'acquisition (#10 #14 #16), le Mode de livraison (#5).

#### R2. Baseline configurable par l'utilisateur *(Faille F3 — 3/18 tests)*
**Module** : `simulation.py`  
**Action** : Ajouter un paramètre optionnel `baseline_value` dans la configuration
de simulation. Si absent, utiliser la dernière valeur du dataset plutôt que la moyenne.  
**Impact** : Changement de 5 à 10 lignes de code. Impact métier immédiat.

#### R3. Régression logistique pour cibles binaires *(3/18 tests)*
**Module** : `regression.py`, `type_detection.py`  
**Action** : Si la colonne cible ne contient que 0 et 1, basculer sur `LogisticRegression`
de `scikit-learn` (ou implémentation native) au lieu de `LinearRegression`.  
**Impact** : Résout le cas Churn (#15) et tout futur cas de classification binaire.

#### R4. Bornes min/max sur les simulations *(1/18 tests)*
**Module** : `simulation.py`  
**Action** : Permettre de passer `bounds=(min_val, max_val)` dans la configuration.
Clipper le résultat de la simulation à ces bornes.  
**Impact** : Résout le cas des notes > 20/20 (#7). Applicable à tout domaine borné.

---

### 🟠 Priorité 2 — Impact significatif, complexité moyenne

#### R5. Détection des distributions asymétriques et transformation log *(Faille F5)*
**Module** : `type_detection.py`, `regression.py`  
**Action** : Calculer le skewness de la colonne cible. Si skewness > 2,0 : signaler dans
les warnings et proposer une transformation logarithmique avant régression.  
**Impact** : Améliore les cas Assurance (#12), Cybersécurité (#16), Industrie (#9).

#### R6. Régression polynomiale degré 2 pour les courbes en U *(Faille F4)*
**Module** : `regression.py`  
**Action** : Si le résidu linéaire présente un pattern quadratique (test de Ramsey RESET
ou simple comparaison $R^2$ linéaire vs polynomiale), utiliser un polynôme degré 2.  
**Impact** : Résout Énergie (#13) et Agriculture (#18) directement.

#### R7. Seuil IQR configurable dans la détection d'anomalies *(Test #1 non couvert)*
**Module** : `anomaly_detection.py`  
**Action** : Permettre de configurer le multiplicateur IQR (actuellement figé) et
d'exclure certaines colonnes de la détection (ex: colonnes de remise ou promotion).  
**Impact** : Élimine les faux positifs sur les remises commerciales normales.

---

### 🟡 Priorité 3 — Impact réel mais complexité élevée, à planifier séparément

#### R8. Warning explicite sur saisonnalité et causalité temporelle *(Test #17)*
**Module** : `report.py`  
**Action** : Détecter la présence d'une colonne temporelle (date, semaine, mois, saison).
Si détectée ET si des corrélations fortes existent, ajouter un warning :
*"Ce dataset contient une dimension temporelle. Les corrélations détectées peuvent
refléter des effets saisonniers plutôt que des relations causales directes."*  
**Note** : Ce warning ne résout pas le problème, mais il prévient l'utilisateur
honnêtement. C'est suffisant et réaliste pour le Niveau 1.

#### R9. Score d'exploitabilité global du fichier *(Audit — Rec. priorité 2)*
**Module** : `report.py`  
**Action** : Calculer un score synthétique à partir du nombre de warnings, du $R^2$,
de la taille de l'échantillon et du nombre d'anomalies. Retourner un verdict :
🟢 Exploitable / 🟡 Interprétation prudente / 🔴 Non exploitable en l'état.  
**Impact** : Améliore massivement l'UX pour les utilisateurs non-statisticiens.

#### R10. Vulgarisation des avertissements *(Audit — Rec. priorité 3)*
**Module** : `report.py`  
**Action** : Doubler chaque warning technique d'une version simplifiée :  
Exemple : au lieu de *"Condition Number élevé (287) : multicolinéarité forte"*,
afficher *"Attention : certaines colonnes de votre fichier sont trop liées entre elles
pour permettre une analyse fiable de leur effet individuel."*

---

## 6. Ce qui reste hors scope réaliste (Niveau 2+)

Ces problèmes sont **réels et prouvés par les tests**, mais leur résolution dépasse
le Niveau 1 de refonte. Les mentionner ici n'est pas un abandon — c'est de la rigueur.

| Problème | Pourquoi c'est Niveau 2+ | Solution qui le résoudrait |
|---|---|---|
| Tarification par paliers (escaliers) | Nécessite une *segmented regression* ou *changepoint detection* — domaine statistique entier | `ruptures`, `pwlf` (Python libs) |
| Biais de variable omise complet | Nécessite une analyse de variance partielle ou une inférence causale | Modèles à effets fixes, DAG |
| Saisonnalité temporelle | Nécessite une décomposition de séries temporelles | `statsmodels` STL, SARIMA |
| Distribution Pareto complète | Nécessite un modèle de mélange ou loi de puissance | Modèles Extreme Value Theory |
| Comparaison de scénarios multiples | Nécessite une refonte de l'API de simulation | Sprint dédié |

---

## 7. Verdict final

> **Les recommandations actuelles du rapport sont une bonne base, mais insuffisantes
> pour traiter la totalité des critiques identifiées.**

Avec les 10 recommandations de ce document (R1 à R10), on atteint **~90% de couverture**
des problèmes prouvés sur les 18 tests. Les 10% restants nécessitent un Niveau 2 de
refonte qui représente chacun un sprint complet.

**L'ordre d'exécution conseillé :**

```
Phase A (2-3 semaines) → R1 + R2 + R4 + R7
  Impact : résoudre 50% des critiques avec les changements les plus localisés.

Phase B (3-4 semaines) → R3 + R5 + R6
  Impact : couvrir les distributions non-gaussiennes et la non-linéarité.

Phase C (2-3 semaines) → R8 + R9 + R10
  Impact : améliorer l'UX, la lisibilité et la transparence du rapport généré.

Phase D (sprint dédié, date à définir) → Changepoint detection + Séries temporelles
  Impact : les 10% restants, nécessite une évaluation séparée.
```

L'outil actuel est un **moteur d'analyse statistique prudent et rigoureux**.
Après ces 3 phases, il deviendra un **moteur d'aide à la décision fiable et honnête**
sur la très grande majorité des cas d'usage métier.
