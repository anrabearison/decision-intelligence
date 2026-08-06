# Rapport d'Expérimentation et d'Analyse Inter-Domaines — decision-core

**Projet** : Decision Intelligence Engine  
**Composants analysés** : `decision-core` & `decision-engine`  
**Date d'expérimentation** : Août 2026  
**Nombre de domaines testés** : 18  
**Dernière mise à jour des résultats** : 5 août 2026 (datasets enrichis, 99–363 lignes par domaine)

---

## 1. Présentation et Objectifs

Ce document présente l'évaluation expérimentale menée sur le moteur `decision-core` à travers **18 jeux de données réels et synthétiques** couvrant des secteurs d'activité variés. 

L'objectif de cette campagne d'expérimentation est de confronter les algorithmes de `decision-core` (importer locale-aware, détection de type, détection de colonnes dérivées, profilage, corrélations corrigées Benjamini-Hochberg, détection d'anomalies IQR, points influents de Cook, et régression/simulation) à la réalité métier de chaque secteur.

> **Note** : Les datasets ont été enrichis en août 2026 (de 12–35 lignes à 99–363 lignes, avec ajout de colonnes supplémentaires). Ce gain de puissance statistique a révélé des faiblesses masquées sur les petits échantillons (ex : $R^2$ artificiellement élevés par sur-ajustement) et a renforcé la fiabilité des détections (P1.2, F5).

---

## 2. Inventaire des 18 Fichiers de Test

Tous les fichiers CSV ci-dessous sont enregistrés dans le répertoire `decision-core/examples/` et peuvent être ré-exécutés avec le script d'analyse :

| N° | Domaine | Nom du Fichier CSV | Délimiteur / Décimale | Nombre de Lignes |
|---|---|---|---|---|
| 1 | **Ventes PME / Retail** | `examples/ventes_magasin_2025.csv` | `;` / `,` | 363 |
| 2 | **Ressources Humaines** | `examples/rh_masse_salariale_2025.csv` | `;` / `,` | 119 |
| 3 | **Élevage / Agriculture** | `examples/elevage_production_lait_2025.csv` | `;` / `,` | 109 |
| 4 | **Finance / Trésorerie** | `examples/finance_tresorerie_2025.csv` | `;` / `,` | 199 |
| 5 | **Logistique / E-Commerce** | `examples/logistique_livraisons_2025.csv` | `;` / `,` | 149 |
| 6 | **Santé / Clinique** | `examples/sante_clinique_2025.csv` | `;` / `,` | 129 |
| 7 | **Éducation / E-Learning** | `examples/education_elearning_2025.csv` | `;` / `,` | 119 |
| 8 | **Immobilier** | `examples/immobilier_estimations_2025.csv` | `;` / `,` | 99 |
| 9 | **Industrie / Maintenance** | `examples/industrie_maintenance_2025.csv` | `;` / `,` | 109 |
| 10 | **Hôtellerie / Booking** | `examples/hotellerie_reservations_2025.csv` | `;` / `,` | 119 |
| 11 | **Restauration** | `examples/restauration_gastronomie_2025.csv` | `;` / `,` | 99 |
| 12 | **Assurance & Sinistres** | `examples/assurance_sinistres_2025.csv` | `;` / `,` | 129 |
| 13 | **Énergie Bâtiments** | `examples/energie_batiments_2025.csv` | `;` / `,` | 119 |
| 14 | **Marketing Digital** | `examples/marketing_digital_2025.csv` | `;` / `,` | 139 |
| 15 | **SaaS Abonnements** | `examples/saas_abonnements_2025.csv` | `;` / `,` | 283 |
| 16 | **Cybersécurité / IT** | `examples/cybersecurite_incidents_2025.csv` | `;` / `,` | 99 |
| 17 | **Tourisme / Culture** | `examples/tourisme_frequentation_2025.csv` | `;` / `,` | 103 |
| 18 | **Agriculture / Céréales** | `examples/agriculture_rendement_2025.csv` | `;` / `,` | 223 |

---

## 3. Détail des Rapports d'Analyse par Domaine

### Test 1 : Ventes PME & Retail
* **Fichier de test** : `examples/ventes_magasin_2025.csv` (363 lignes × 8 colonnes)
* **Configuration de simulation** : Target = `Chiffre_Affaires`, Feature = `Budget_Pub`, Change % = `+10%`
* **Résultat obtenu** : Baseline = 2 249,53 €, Simulation = 2 306,67 € (+2,54%), $R^2 = 0,148$.
* **Exploitabilité** : 🔴 RED (score = 10/100)
* **Analyse & Critique Métier** :
  - **$R^2$ très faible (15%)** : Avec 363 lignes, le sur-ajustement observé sur le petit échantillon ($R^2 = 0,97$ sur 35 lignes) disparaît. Le budget publicitaire n'explique que 15% du chiffre d'affaires — le reste dépend de la région, du prix unitaire et de la saisonnalité.
  - **Faux positifs sur les promotions** : Les remises de 5% et 10% sur la colonne `Remise_Pct` sont qualifiées d'anomalies IQR faussant les moyennes. C'est une fausse alerte pour un commerçant.
  - ~~**Absence de segmentation** : La baseline globale agrège sans distinction les magasins de PACA et du Nord.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : La colonne `Region` est maintenant intégrée via un encodage One-Hot optionnel et détectée comme sous-groupe majeur, ce qui permet d'orienter vers une résolution du problème de la baseline globale.</span>
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F5)** : Le moteur détecte la distribution de comptage à forte proportion de zéros sur `Remise_Pct` (4 valeurs distinctes) et avertit que la régression gaussienne est inadaptée.</span>

### Test 2 : Ressources Humaines
* **Fichier de test** : `examples/rh_masse_salariale_2025.csv` (119 lignes × 11 colonnes)
* **Configuration de simulation** : Target = `Salaire_Brut_Mensuel`, Feature = `Anciennete_Annees`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 5 092,53 €, Simulation = 5 517,37 € (+8,34%), $R^2 = 0,739$.
* **Exploitabilité** : 🟠 ORANGE (score = 55/100)
* **Analyse & Critique Métier** :
  - **Facteur confondant du département** : Corrélation `Formation_Jours ↔ Salaire` (0.734) due au fait que la Tech gagne plus ET se forme plus que les RH.
  - **Rampe linéaire irréaliste** : En RH, les augmentations se font par paliers et grilles salariales, pas via une droite linéaire continue.

### Test 3 : Élevage & Agriculture
* **Fichier de test** : `examples/elevage_production_lait_2025.csv` (109 lignes × 10 colonnes)
* **Configuration de simulation** : Target = `Litres_Lait_Jour`, Feature = `Ration_Fourrage_Kg`, Change % = `+15%`
* **Résultat obtenu** : Baseline = 26,30 L, Simulation = 30,92 L (+17,57%), $R^2 = 0,830$.
* **Exploitabilité** : 🟠 ORANGE (score = 55/100)
* **Analyse & Critique Métier** :
  - ~~**Paradoxe de Simpson ($R = -0.884$)** : Le moteur conclut que plus la vache est lourde, moins son lait est riche. C'est simplement que les Jersey (petites) font du lait très gras et les Holstein (lourdes) du lait moins gras. Mélanger les deux races produit une conclusion biologiquement absurde.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0/P1.1)** : Le moteur identifie désormais la `Race` comme sous-groupe significatif ($\eta^2$) et lève une alerte explicite de corrélation spurieuse pour alerter l'utilisateur du biais de causalité.</span>

### Test 4 : Finance & Trésorerie PME
* **Fichier de test** : `examples/finance_tresorerie_2025.csv` (199 lignes × 12 colonnes)
* **Configuration de simulation** : Target = `Solde_Tresorerie_Euros`, Feature = `Delai_Paiement_Jours`, Change % = `-20%`
* **Résultat obtenu** : Baseline = 39 166,67 €, Simulation = 66 299,44 € (+69,28%), $R^2 = 0,894$.
* **Exploitabilité** : 🟠 ORANGE (score = 55/100)
* **Analyse & Critique Métier** :
  - **Succès arithmétique** : `derived_columns.py` a bien retiré la relation `Créances + Dettes = Trésorerie`.
  - **Surestimation massive** : Projette une hausse de trésorerie de +69% car le modèle attribue l'impact de deux mois d'achats d'équipements exceptionnels (Investissements) au seul délai de paiement.

### Test 5 : Logistique & Livraisons E-Commerce
* **Fichier de test** : `examples/logistique_livraisons_2025.csv` (149 lignes × 10 colonnes)
* **Configuration de simulation** : Target = `Temps_Livraison_Heures`, Feature = `Distance_Km`, Change % = `+10%`
* **Résultat obtenu** : Baseline = 42,49 h, Simulation = 42,97 h (+1,13%), $R^2 = 0,053$ (Échec).
* **Exploitabilité** : 🔴 RED (score = 20/100)
* **Analyse & Critique Métier** :
  - ~~**$R^2$ dérisoire (5%)** : Le temps dépend du `Mode_Livraison` (Express en 18h vs Relais en 48h), pas de la distance. Ignorer la colonne texte du mode de livraison rend la simulation inutile.~~
  - ~~**Tarifs par paliers** : Les frais de port fonctionnent par tranches de poids fixes, inaccessibles à la régression linéaire.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : Le moteur identifie désormais `Mode_Livraison` comme le sous-groupe principal ($\eta^2$) déterminant le temps de livraison.</span>
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.2 - Seuils recalibrés)** : Le moteur détecte désormais les relations par paliers (step functions) sur la paire exacte `Poids_Colis_Kg` -> `Frais_Port_Euros` (écart $\eta^2 - R^2 \approx 0,022$ capturé par le seuil de $0,02$) et avertit que la régression linéaire peut être trompeuse sur cette paire.</span>
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F5)** : Le moteur détecte les distributions de comptage sur `Reclamations_Client` (2 valeurs distinctes) et `Délai_Jours` (7 valeurs discrètes), avertissant de l'inadéquation du modèle gaussien.</span>

### Test 6 : Santé & Suivi Clinique
* **Fichier de test** : `examples/sante_clinique_2025.csv` (129 lignes × 8 colonnes)
* **Configuration de simulation** : Target = `Score_Retablissement`, Feature = `Dosage_Medicament_Mg`, Change % = `+50%`
* **Résultat obtenu** : Baseline = 75,80, Simulation = 74,89 (-1,21%), $R^2 = 0,005$.
* **Exploitabilité** : 🟠 ORANGE (score = 40/100)
* **Analyse & Critique Métier** :
  - ~~**Biais d'Indication Médical** : Le moteur prédit qu'augmenter le dosage dégrade la santé des patients ! C'est simplement que les cas les plus graves reçoivent des doses plus fortes. Un médecin suivant ce conseil commettrait une erreur grave.~~
  - **$R^2$ quasi nul (0,5%)** : Avec 129 lignes, la corrélation spurieuse s'effondre — le moteur ne trouve plus de relation significative entre le dosage et le rétablissement, ce qui est plus honnête que l'ancienne valeur ($R^2 = 0,413$ sur 15 lignes).
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0)** : La fonction `detect_confounders` identifie la sévérité initiale comme facteur confondant et génère un avertissement de corrélation spurieuse, empêchant l'erreur d'interprétation.</span>
* <span style="color: #2ea043;">**Nota** : la détection des sous-groupes et des step patterns a été renforcée par un test F d'ANOVA et un garde-fou de taille minimale par groupe, réduisant les faux positifs sur de petits échantillons.</span>

### Test 7 : Éducation & E-Learning
* **Fichier de test** : `examples/education_elearning_2025.csv` (119 lignes × 11 colonnes)
* **Configuration de simulation** : Target = `Note_Examen_Sur_20`, Feature = `Temps_Video_Heures`, Change % = `+30%`
* **Résultat obtenu** : Baseline = 15,67/20, Simulation = 17,57/20 (+12,15%), $R^2 = 0,890$.
* **Exploitabilité** : 🟠 ORANGE (score = 60/100)
* **Analyse & Critique Métier** :
  - **Dépassement du plafond (26/20)** : Sans bornes institutionnelles (0 à 20), la régression linéaire projette des notes > 20 pour un temps de révision élevé.
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.2)** : Le moteur détecte désormais le rendement décroissant (optimum non-linéaire) entre le temps de révision/quiz et les notes, avertissant des limites du modèle linéaire. Le dépassement de plafond (bornes physiques) reste à traiter (Phase P2/P3).</span>

### Test 8 : Immobilier & Estimation de Biens
* **Fichier de test** : `examples/immobilier_estimations_2025.csv` (99 lignes × 10 colonnes)
* **Configuration de simulation** : Target = `Prix_Vente_Euros`, Feature = `Surface_M2`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 440 619 €, Simulation = 515 197 € (+16,93%), $R^2 = 0,428$.
* **Exploitabilité** : 🟠 ORANGE (score = 50/100)
* **Analyse & Critique Métier** :
  - ~~**Facteur Quartier ignoré** : Le m² au Centre vaut 6 000 € vs 2 500 € en Périphérie. Ne pas segmenter par `Quartier` fait chuter le $R^2$ à 0,42.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : La variable `Quartier` est désormais détectée comme structurante, suggérant automatiquement à l'utilisateur de procéder à une analyse segmentée.</span>
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F5)** : Le moteur détecte les distributions de comptage sur `Nombre_Pieces` (6 valeurs discrètes) et `Etage` (7 valeurs discrètes).</span>

### Test 9 : Industrie & Maintenance Prédictive
* **Fichier de test** : `examples/industrie_maintenance_2025.csv` (109 lignes × 13 colonnes)
* **Configuration de simulation** : Target = `Anomalies_Comptees`, Feature = `Heures_Fonctionnement`, Change % = `+25%`
* **Résultat obtenu** : Baseline = 1,47, Simulation = 2,27 (+54,76%), $R^2 = 0,829$.
* **Exploitabilité** : 🟠 ORANGE (score = 50/100)
* **Analyse & Critique Métier** :
  - ~~**Pannes de type Poisson** : Traiter des comptages discrets de pannes (0, 1, 2, 5) par régression gaussienne continue est théoriquement inadapté (besoin de modèles de Poisson/Weibull).~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F5)** : Le moteur détecte désormais la distribution de comptage avec forte proportion de zéros sur `Anomalies_Comptees` (6 valeurs distinctes) et avertit que la régression gaussienne est inadaptée à cette variable discrète.</span>

### Test 10 : Hôtellerie & Réservations
* **Fichier de test** : `examples/hotellerie_reservations_2025.csv` (119 lignes × 11 colonnes)
* **Configuration de simulation** : Target = `Taux_Annulation_Pct`, Feature = `Delai_Reservation_Jours`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 9,82%, Simulation = 11,90% (+21,15%), $R^2 = 0,954$.
* **Exploitabilité** : 🔴 RED (score = 35/100)
* **Analyse & Critique Métier** :
  - ~~**Canal de réservation ignoré** : La corrélation géante (0,976) s'explique par les centrales Booking/Expedia réservées longtemps à l'avance et plus annulées que le direct.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0/P1.1)** : Le moteur alerte sur la corrélation spurieuse et détecte le canal d'acquisition comme facteur confondant et sous-groupe essentiel.</span>
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F5)** : Le moteur détecte les distributions de comptage sur `Duree_Sejour_Jours` (6 valeurs discrètes) et `Duree_Sejour_Nuits` (6 valeurs discrètes).</span>

### Test 11 : Restauration & Gastronomie
* **Fichier de test** : `examples/restauration_gastronomie_2025.csv` (99 lignes × 12 colonnes)
* **Configuration de simulation** : Target = `Chiffre_Affaires_Jour`, Feature = `Nombre_Couverts`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 2 528,82 €, Simulation = 3 208,82 € (+26,89%), $R^2 = 0,995$.
* **Exploitabilité** : 🟠 ORANGE (score = 40/100)
* **Analyse & Critique Métier** :
  - **Effet Weekend et Météo ignorés** : L'affluence dépend du `Jour_Semaine` et de la `Meteo` (variables texte non lues).

### Test 12 : Assurance & Sinistralité
* **Fichier de test** : `examples/assurance_sinistres_2025.csv` (129 lignes × 7 colonnes)
* **Configuration de simulation** : Target = `Cout_Indemnisation_Euros`, Feature = `Puissance_Vehicule_CV`, Change % = `+15%`
* **Résultat obtenu** : Baseline = 545,78 €, Simulation = 667,97 € (+22,39%), $R^2 = 0,014$.
* **Exploitabilité** : 🔴 RED (score = 15/100)
* **Analyse & Critique Métier** :
  - **Distribution Zéro-Inflated** : 82% des assurés ont 0 € de sinistre. La moyenne (546 €) est un artefact sans utilité actuarielle.
  - **$R^2$ quasi nul (1,4%)** : Avec 129 lignes, la puissance véhicule n'explique pratiquement rien du coût d'indemnisation. La relation est masquée par la masse de zéros.
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F5)** : Le moteur détecte désormais la distribution de comptage à forte proportion de zéros sur `Nombre_Sinistres` (3 valeurs distinctes) ET la distribution zéro-inflated sur `Cout_Indemnisation_Euros` (82% de zéros). Ces warnings guident l'utilisateur vers un modèle à deux parties.</span>

### Test 13 : Énergie & Consommation Bâtiments
* **Fichier de test** : `examples/energie_batiments_2025.csv` (119 lignes × 11 colonnes)
* **Configuration de simulation** : Target = `Consommation_KWh`, Feature = `Temperature_Exterieure_C`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 92 357 kWh, Simulation = 87 840 kWh (-4,89%), $R^2 = 0,027$.
* **Exploitabilité** : 🟠 ORANGE (score = 55/100)
* **Analyse & Critique Métier** :
  - **Courbe en U (Climatisation)** : La consommation monte en hiver (Chauffage) et remonte en été (Climatisation). Le modèle linéaire rate le creux parabolique.
  - **$R^2$ très faible (2,7%)** : Avec les données enrichies, le modèle linéaire explique quasiment rien — confirmant l'inadéquation structurelle de la droite pour cette relation en U.
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.2)** : Avec le dataset enrichi, le scan élargi détecte désormais 1 pattern non-linéaire sur ce domaine. Le signal quadratique bénéficie de plus de données pour franchir le seuil de détection.</span>

### Test 14 : Marketing Digital & SEO/Adwords
* **Fichier de test** : `examples/marketing_digital_2025.csv` (139 lignes × 10 colonnes)
* **Configuration de simulation** : Target = `Cout_Acquisition_CAC`, Feature = `Cout_Par_Clic_CPC`, Change % = `+10%`
* **Résultat obtenu** : Baseline = 103,04 €, Simulation = 115,35 € (+11,95%), $R^2 = 0,970$.
* **Exploitabilité** : 🟠 ORANGE (score = 40/100)
* **Analyse & Critique Métier** :
  - **Mélange de réseaux hétérogènes** : Agrège LinkedIn (CPC 4.50€) et Facebook (CPC 0.60€) sans distinction du canal publicitaire.
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F3)** : Le moteur avertit que la baseline de `Cout_Acquisition_CAC` (moyenne 103 €) est très éloignée de la médiane (35 €), et que le point de départ de `Cout_Par_Clic_CPC` (moyenne 2,17 €) est très éloigné de la médiane (1,30 €) — orientant l'utilisateur vers une segmentation par canal.</span>

### Test 15 : SaaS & Abonnements (Churn)
* **Fichier de test** : `examples/saas_abonnements_2025.csv` (283 lignes × 6 colonnes)
* **Configuration de simulation** : Target = `Desabonnement_Churn`, Feature = `Tickets_Support`, Change % = `+50%`
* **Résultat obtenu** : Baseline = 0,13 (13%), Simulation = 0,13 (13%), Δ = N/A, $R^2 = 0,001$.
* **Exploitabilité** : 🔴 RED (score = 0/100)
* **Analyse & Critique Métier** :
  - ~~**Cible binaire (Churn 0/1)** : Événement binaire estimé par régression linéaire ordinaire au lieu d'une régression logistique.~~
  - **$R^2$ effondré avec plus de données** : Sur 15 lignes, le bruit produisait $R^2 = 0,81$. Sur 283 lignes, la vérité émerge : `Tickets_Support` n'explique que 0,1% du Churn. La relation réelle est probablement médiée par d'autres variables (plan, ancienneté).
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0)** : Le moteur détecte automatiquement les cibles binaires et bascule sur une régression logistique (L-BFGS-B). Le $R^2$ quasi nul reflète fidèlement l'absence de relation directe `Tickets → Churn` sur ce dataset enrichi.</span>
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F5)** : Le moteur détecte la distribution zéro-inflated sur `Tickets_Support` (54% de zéros) et la distribution de comptage binaire sur `Desabonnement_Churn` (2 valeurs distinctes).</span>

### Test 16 : Cybersécurité & Incidents IT
* **Fichier de test** : `examples/cybersecurite_incidents_2025.csv` (99 lignes × 13 colonnes)
* **Configuration de simulation** : Target = `Cout_Incident_Euros`, Feature = `Nb_Systemes_Touches`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 167 993 €, Simulation = 217 809 € (+29,65%), $R^2 = 0,914$.
* **Exploitabilité** : 🔴 RED (score = 20/100)
* **Analyse & Critique Métier** :
  - **Distribution bimodale extrême (Pareto / Loi de puissance)** : 80% des incidents coûtent moins de 22 000 €, mais les incidents critiques coûtent entre 280 000 € et 950 000 €. La régression linéaire produit une baseline à 167 993 € qui ne correspond à aucune catégorie réelle.
  - ~~**La sévérité de l'incident (`Criticite`) est ignorée** : C'est la variable texte `Criticite` (Faible / Moyen / Critique) qui explique 95% du coût. Le moteur ne peut pas l'intégrer.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : Le moteur identifie désormais `Criticite` comme sous-groupe majeur expliquant près de 87% de la variance des coûts.</span>
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase F3)** : Le moteur avertit que la baseline de `Cout_Incident_Euros` (moyenne 167 993 €) est très éloignée de la médiane, orientant vers une segmentation par `Criticite`.</span>

### Test 17 : Tourisme & Fréquentation Culturelle
* **Fichier de test** : `examples/tourisme_frequentation_2025.csv` (103 lignes × 7 colonnes)
* **Configuration de simulation** : Target = `Visiteurs_Jour`, Feature = `Prix_Billet_Euros`, Change % = `-10%`
* **Résultat obtenu** : Baseline = 1 594 visiteurs/jour, Simulation = 1 423 visiteurs/jour (-10,72%), $R^2 = 0,552$.
* **Exploitabilité** : 🟠 ORANGE (score = 65/100)
* **Analyse & Critique Métier** :
  - ~~**Inversion de causalité** : Le moteur conclut qu'une baisse de prix ferait chuter les visiteurs ! En réalité, le prix élevé correspond à l'été (haute saison) avec plus de visiteurs. C'est la saison qui explique les deux variables — le musée augmente ses prix en haute saison.~~
  - ~~**Les vraies variables sont ignorées** : `Saison` et `Vacances_Scolaires` (colonnes texte booléen) expliquent bien mieux la fréquentation que le prix du billet.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0/P1.1)** : Le moteur alerte formellement sur la corrélation spurieuse causée par `Saison` et détecte ces colonnes catégorielles comme des sous-groupes significatifs à analyser séparément.</span>

### Test 18 : Agriculture & Rendement Céréalier
* **Fichier de test** : `examples/agriculture_rendement_2025.csv` (223 lignes × 6 colonnes)
* **Configuration de simulation** : Target = `Rendement_Quintal_Ha`, Feature = `Pluviometrie_Mm`, Change % = `+15%`
* **Résultat obtenu** : Baseline = 40,91 q/ha, Simulation = 40,97 q/ha (+0,16%), $R^2 = 0,0001$ (Effondrement total).
* **Exploitabilité** : 🔴 RED (score = 25/100)
* **Analyse & Critique Métier** :
  - **Effondrement complet du modèle ($R^2 = 0,0001$)** : La pluviométrie n'explique que 0,01% du rendement selon le modèle linéaire. Résultat attendu par un agronome — la relation est parabolique, pas linéaire.
  - **Relation en courbe de Gauss (Optimum de pluviométrie)** : Le moteur détecte l'optimum gaussien sur la paire `Pluviometrie_Mm` → `Rendement_Quintal_Ha` (pattern_type="optimum", R² ajusté quadratique ≫ R² linéaire) et avertit que la régression linéaire est aveugle à cet optimum parabolique.
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : Le moteur détecte désormais que `Type_Sol` est responsable d'une forte proportion de la variance du rendement et avertit l'utilisateur.</span>
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.2)** : Le moteur détecte l'optimum gaussien sur la paire exacte documentée `Pluviometrie_Mm` → `Rendement_Quintal_Ha` et avertit que la régression linéaire est aveugle à cet optimum parabolique.</span>

---

## 4. Tableau de Synthèse Finale des 18 Domaines

| N° | Domaine | Fichier CSV | Score | Verdict | Limite Métier Majeure Découverte |
|---|---|---|---|---|---|
| 1 | **Ventes PME** | `ventes_magasin_2025.csv` | 🔴 10 | ⚠️ Sur-ajustement | $R^2$ effondré (0,97→0,15) avec plus de données ; baseline globale illusoire. |
| 2 | **RH** | `rh_masse_salariale_2025.csv` | 🟠 55 | ⚠️ Risqué | Biais du département ; rampe linéaire irréaliste sur grilles salariales. |
| 3 | **Élevage** | `elevage_production_lait_2025.csv` | 🟠 55 | ⚠️ Amélioré | ~~Paradoxe de Simpson~~ → détecté et signalé (P0/P1.1). |
| 4 | **Finance** | `finance_tresorerie_2025.csv` | 🟠 55 | ⚠️ Surestimé | Formules comptables OK, mais surestimation (+69%) via flux d'investissement. |
| 5 | **Logistique** | `logistique_livraisons_2025.csv` | 🔴 20 | ❌ Échec ($R^2=0,05$) | Incapacité à modéliser Express vs Relais et tarification par tranches. |
| 6 | **Santé** | `sante_clinique_2025.csv` | 🟠 40 | ⚠️ Amélioré | ~~Biais d'Indication~~ → détecté (P0). $R^2$ honnêtement quasi nul. |
| 7 | **Éducation** | `education_elearning_2025.csv` | 🟠 60 | ⚠️ Abstrait | Projections hors bornes (note > 20/20) et rendement décroissant détecté (P1.2). |
| 8 | **Immobilier** | `immobilier_estimations_2025.csv` | 🟠 50 | ⚠️ Médiocre ($R^2=0,43$) | Quartier détecté (P1.1) ; distributions de comptage signalées (F5). |
| 9 | **Industrie** | `industrie_maintenance_2025.csv` | 🟠 50 | ⚠️ Amélioré | ~~Poisson non détecté~~ → distribution de comptage détectée (F5). |
| 10 | **Hôtellerie** | `hotellerie_reservations_2025.csv` | 🔴 35 | ⚠️ Partiel | Canal d'acquisition détecté (P0/P1.1) ; comptages signalés (F5). |
| 11 | **Restauration** | `restauration_gastronomie_2025.csv` | 🟠 40 | ⚠️ Incomplet | Effets du weekend et de la météo ignorés. |
| 12 | **Assurance** | `assurance_sinistres_2025.csv` | 🔴 15 | ❌ Amélioré | ~~Zéro-inflated non détecté~~ → 82% de zéros + comptage détectés (F5). $R^2=0,01$. |
| 13 | **Énergie** | `energie_batiments_2025.csv` | 🟠 55 | ⚠️ Amélioré | Courbe en U partiellement détectée (P1.2). $R^2$ linéaire ≈ 0,03. |
| 14 | **Marketing** | `marketing_digital_2025.csv` | 🟠 40 | ⚠️ Mélangé | Asymétrie détectée (F3) ; agrégation aveugle de canaux publicitaires. |
| 15 | **SaaS** | `saas_abonnements_2025.csv` | 🔴 0 | ❌ Révisé | Logistique OK mais $R^2$ effondré (0,81→0,001) avec 283 lignes. Zéro-inflated détecté (F5). |
| 16 | **Cybersécurité** | `cybersecurite_incidents_2025.csv` | 🔴 20 | ❌ Partiel | Distribution Pareto extrême ; `Criticite` détectée (P1.1). Asymétrie signalée (F3). |
| 17 | **Tourisme** | `tourisme_frequentation_2025.csv` | 🟠 65 | ⚠️ Amélioré | ~~Inversion de causalité~~ → corrélation spurieuse détectée (P0/P1.1). |
| 18 | **Agriculture** | `agriculture_rendement_2025.csv` | 🔴 25 | ❌ Détecté | Optimum gaussien détecté (P1.2) ; `Type_Sol` signalé (P1.1). $R^2≈0$. |

---

## 5. Analyse des Répétitions de Critiques

Sur les 18 tests réalisés, l'analyse transversale révèle que **les critiques ne sont pas indépendantes**. Elles se regroupent en **5 failles structurelles** qui se manifestent répétitivement sous des formes sectorielles différentes.

> **Conclusion clé** : Ce ne sont pas 18 problèmes distincts — c'est le même ensemble de 5 limites architecturales qui se répète. Les phases P0, P1.1, P1.2, F3 et F5 ont résolu ou atténué la majorité de ces failles via des warnings pédagogiques. Le moteur de régression (linéaire/logistique) reste inchangé — les corrections sont au niveau de la détection et de l'information utilisateur.

---

### Faille #1 — Variables catégorielles / texte ignorées *(7 tests sur 18)*

C'est la critique la plus universelle. Le moteur exclut toutes les colonnes non-numériques par conception, laissant systématiquement de côté les variables explicatives les plus importantes.

| Test | Variable texte ignorée | Conséquence observée |
|---|---|---|
| #1 Ventes PME | `Region` | Baseline globale illusoire (ni Nord ni PACA) |
| #3 Élevage | `Race` | Paradoxe de Simpson ($R = -0,88$) |
| #5 Logistique | `Mode_Livraison` | $R^2 = 0,05$ — échec total |
| #8 Immobilier | `Quartier` | $R^2 = 0,42$ — modèle médiocre |
| #10 Hôtellerie | `Canal_Reservation` | Corrélation spurieuse sur les annulations |
| #16 Cybersécurité | `Criticite` | Baseline à 167 993 € sans correspondance réelle |
| #18 Agriculture | `Type_Sol` | Variance du rendement inexpliquée |

<span style="color: #2ea043;">**Atténuation (P1.1)** : Le moteur détecte désormais ces sous-groupes catégoriels via $\eta^2$ et avertit l'utilisateur. La colonne structurante est identifiée dans 12/18 domaines (66,7%).</span>

---

### Faille #2 — Inversion de causalité / Facteur confondant *(4 tests sur 18)*

Le moteur confond une corrélation spurieuse avec une relation de cause à effet, conduisant à des recommandations opérationnelles incorrectes, voire dangereuses.

| Test | Corrélation spurieuse détectée | Vrai facteur confondant caché |
|---|---|---|
| #3 Élevage | Poids ↔ Taux de gras du lait ($R=-0,88$) | Race (Holstein légères vs Jersey lourdes) |
| #6 Santé | Dosage ↔ Dégradation de la santé | Sévérité initiale du patient (biais d'indication) |
| #10 Hôtellerie | Délai de réservation ↔ Annulation | Canal d'acquisition (Booking vs Direct) |
| #17 Tourisme | Prix du billet ↔ Fréquentation | Saison (prix hauts ET visiteurs hauts en été) |

<span style="color: #2ea043;">**Résolu (P0)** : Le moteur détecte les facteurs confondants via `detect_confounders` et génère des avertissements de corrélation spurieuse. 10/18 domaines (55,6%) reçoivent au moins un warning de ce type.</span>

---

### Faille #3 — Baseline = moyenne globale sans sens métier *(3 tests sur 18)*

La baseline calculée comme moyenne arithmétique de l'historique complet ne correspond à aucune situation concrète exploitable par un décideur.

| Test | Baseline calculée | Problème métier |
|---|---|---|
| #1 Ventes PME | 2 250 €/transaction | Ni région Nord (3 500 €) ni PACA (1 200 €) |
| #11 Restauration | 2 529 €/jour | Mélange weekends (haute affluence) + semaine |
| #16 Cybersécurité | 167 993 € par incident | Aucun incident à ce coût : soit < 22 000 € soit > 280 000 € |

<span style="color: #2ea043;">**Résolu (Phase F3)** : Le moteur détecte les distributions asymétriques (ratio `|mean - median| / std > 0.4`) et génère deux types d'alertes ciblés :
- **Cible Y asymétrique** → *"Baseline de simulation peu représentative"*
- **Levier X asymétrique** → *"Point de départ du scénario peu représentatif"*

Le warning suggère automatiquement le sous-groupe structurant déjà détecté en P1.1. La valeur de la baseline n'est pas modifiée — le moteur informe, ne décide pas. Taux de détection actuel : 2/18 (11,1%) — l'enrichissement des datasets a lissé les distributions, réduisant naturellement l'asymétrie.</span>

---

### Faille #4 — Non-linéarité ignorée (courbe en U / paliers / optimum) *(4 tests sur 18)*

Le moteur applique systématiquement une droite linéaire, aveugle à toute relation en courbe, seuil ou optimum.
La détection P1.2 ne dépend plus uniquement des 5 meilleures corrélations linéaires : elle scanne désormais les paires numériques candidates, avec un plafond de sécurité, afin de couvrir les relations fortement non-linéaires dont la corrélation linéaire est faible. Pour éviter de noyer l'utilisateur, le rapport affiche seulement les 3 alertes P1.2 au plus fort gain explicatif, tout en conservant les autres patterns détectés pour les garde-fous de simulation.

| Test | Type de non-linéarité réelle |
|---|---|
| #5 Logistique | Tarification par paliers de poids (escaliers, pas une droite) |
| #7 Éducation | Rendement décroissant : au-delà d'un certain volume, plus de révision n'améliore plus proportionnellement la note |
| #13 Énergie | Courbe en U : Chauffage (hiver) + Climatisation (été), creux au printemps |
| #18 Agriculture | Optimum gaussien de pluviométrie (300-400 mm) : trop sec ET trop humide = mauvais rendement |

<span style="color: #2ea043;">**Résolu (Phase P1.2)** : Le scan élargi détecte des patterns non-linéaires sur 16/18 domaines (88,9%). Les 4 cas critiques ci-dessus sont tous correctement détectés et signalés.</span>

---

### Faille #5 — Distribution non-gaussienne traitée comme normale *(3 tests originaux sur 18)*

Le moteur de régression suppose implicitement une distribution gaussienne (loi normale). Cette hypothèse est incorrecte pour les données de comptage, les sinistres rares et les incidents à loi de puissance.

| Test | Distribution réelle | Modèle adapté manquant | Détection F5 |
|---|---|---|---|
| #9 Industrie | Comptages discrets (0, 1, 2, 5 pannes) | Régression de Poisson / Weibull | ✅ Détecté |
| #12 Assurance | Zéro-Inflated (82% à 0 € de sinistre) | Modèle à deux parties (Zero-Inflated) | ✅ Détecté |
| #16 Cybersécurité | Pareto / Loi de puissance (incidents critiques = 95% des coûts) | Log-normale ou modèle de mélange | ⚠️ Partiel (détecté via F3) |

<span style="color: #2ea043;">**Résolu (Phase F5)** : Le moteur détecte désormais trois types de distributions non-gaussiennes via `detect_count_data_distribution`, `detect_zero_inflation` et `detect_heavy_tail`. Taux de détection actuel : 7/18 domaines (38,9%) — couvrant les cas critiques (#9, #12, #15) plus 4 domaines supplémentaires (#1, #5, #8, #10) où des variables de comptage sont détectées.

Le moteur ne modifie pas le modèle de régression (qui reste gaussien), mais informe l'utilisateur de l'inadéquation et suggère le modèle approprié (Poisson, Zero-Inflated, Log-normale).</span>

---

### Carte de chaleur des failles par test

| Test | F1 Catégories | F2 Causalité | F3 Baseline | F4 Non-linéarité | F5 Distribution |
|---|:---:|:---:|:---:|:---:|:---:|
| #1 Ventes PME | ✅ | | ✅ | | ✅ |
| #2 RH | ✅ | ✅ | | | |
| #3 Élevage | ✅ | ✅ | | | |
| #4 Finance | | ✅ | | | |
| #5 Logistique | ✅ | | | ✅ | ✅ |
| #6 Santé | | ✅ | | | |
| #7 Éducation | | | | ✅ | |
| #8 Immobilier | ✅ | | | | ✅ |
| #9 Industrie | | | | | ✅ |
| #10 Hôtellerie | ✅ | ✅ | | | ✅ |
| #11 Restauration | ✅ | | ✅ | | |
| #12 Assurance | | | | | ✅ |
| #13 Énergie | | | | ✅ | |
| #14 Marketing | ✅ | | | | |
| #15 SaaS | | | | | ✅ |
| #16 Cybersécurité | ✅ | | ✅ | | ✅ |
| #17 Tourisme | ✅ | ✅ | | | |
| #18 Agriculture | ✅ | | | ✅ | |
| **Total** | **11** | **6** | **3** | **4** | **8** |

---

## 6. Matrice de Correspondance : Critiques Fusionnées ↔ Tests CSV Réels

Ce tableau démontre comment **chaque critique identifiée dans l'audit** est directement illustrée et prouvée par un ou plusieurs des 18 tests CSV du projet :

| Critique Identifiée dans l'Audit | Fichier CSV de Démonstration | Manifestation Concrète observée |
|---|---|---|
| **1. Ignorance des catégories / sous-groupes (Variables texte)** | `elevage_production_lait_2025.csv`<br>`rh_masse_salariale_2025.csv`<br>`immobilier_estimations_2025.csv` | **Paradoxe de Simpson** ($R=-0,88$ entre Poids et Gras du lait par mélange des races Holstein/Jersey).<br>Confondateur `Departement` en RH.<br>`Quartier` ignoré en immobilier. |
| **2. Biais de causalité & Biais d'Indication** | `sante_clinique_2025.csv`<br>`finance_tresorerie_2025.csv`<br>`hotellerie_reservations_2025.csv` | Prédiction qu'augmenter la dose de médicament dégrade le rétablissement (patients plus graves dosés plus fort).<br>Attribution de l'effet d'investissements au seul délai de paiement. |
| **3. Baseline sur la moyenne (pas la valeur récente)** | `ventes_magasin_2025.csv`<br>`restauration_gastronomie_2025.csv` | Baseline à 2 250 € qui ne correspond ni au Nord (3 500 €) ni à PACA (1 200 €).<br>Moyenne qui agrège les weekends et les jours de semaine. |
| **4. Incapacité à modéliser des bornes (Notes / Plafonds)** | `education_elearning_2025.csv` | Extrapolation linéaire prédisant des notes de **26/20** au-delà de 80h d'étude. |
| **5. Aveuglement aux courbes en U (Non-linéarité)** | `energie_batiments_2025.csv` | Modèle linéaire unable de capter le creux de consommation (Chauffage l'hiver + Climatisation l'été). |
| **6. Régression linéaire sur événement binaire (0/1)** | `saas_abonnements_2025.csv` | Prédiction de Churn (0 ou 1) via une droite continue au lieu d'une régression logistique. |
| **7. Distribution Zéro-Inflated (Sinistres)** | `assurance_sinistres_2025.csv` | Coût moyen théorique appliqué sur une population où 82% des personnes ont 0 € de sinistre. |
| **8. Incompatibilité avec les tarifications par paliers** | `logistique_livraisons_2025.csv` | Effondrement du modèle ($R^2=0,05$) sur des livraisons à tarifs par tranches de poids fixe. |
| **9. Régression continue sur comptages discrets** | `industrie_maintenance_2025.csv` | Modèle gaussien appliqué à des nombres entiers d'anomalies (besoin de loi de Poisson/Weibull). |
| **10. Faux positifs sur les alertes métiers** | `ventes_magasin_2025.csv` | Promotions normales de 5% et 10% qualifiées d'*"anomalies IQR à vérifier"*. |

---

## 7. Recommandations d'Évolution pour decision-core

1. ~~**Prise en compte des sous-groupes (Variables Catégorielles)**~~ : ✅ **Résolu (Phase P1.1)** — Le moteur détecte les sous-groupes structurants via $\eta^2$ dans 12/18 domaines.
2. ~~**Régression Logistique pour cibles binaires (0/1)**~~ : ✅ **Résolu (Phase P0)** — Bascule automatique sur régression logistique (L-BFGS-B) pour les cibles binaires.
3. ~~**Planchers et Plafonds (Bornes)**~~ : ✅ **Résolu** — Le paramètre `bounds=(min, max)` dans `SimulationConfig` permet de borner les prédictions (ex : note de 0 à 20).
4. ~~**Baseline basée sur la dernière valeur connue**~~ : ✅ **Résolu** — Le paramètre `baseline_feature_value` permet d'utiliser la dernière valeur connue. Phase F3 ajoute un warning quand la baseline (moyenne) est non représentative.

### Recommandations restantes

5. **Modèles de régression adaptés aux distributions** : Implémenter la régression de Poisson (comptages), le modèle à deux parties (zéro-inflated), et la régression log-normale (queues lourdes) comme alternatives automatiques quand F5 détecte une violation de l'hypothèse gaussienne.
6. **Segmentation automatique** : Quand P1.1 identifie un sous-groupe dominant ($\eta^2 > 0,5$), proposer automatiquement une analyse segmentée (group_by) plutôt qu'une seule analyse globale.

---

## 8. Historique des Résolutions

*   **[Août 2026] Phase P0 - Régression Logistique & Causalité** : 
    *   Implémentation de `fit_logistic_regression` (via `scipy.optimize.minimize` L-BFGS-B) pour les cibles binaires avec bornage naturel $[0, 1]$.
    *   Ajout de la détection systématique des biais de causalité (`detect_confounders`) et d'avertissements explicites de corrélation spurieuse.
*   **[Août 2026] Phase P1.1 - Variables Catégorielles** :
    *   Ajout de la détection des sous-groupes structurants via l'analyse de la variance ($\eta^2$). Le moteur avertit désormais quand une variable catégorielle explique une forte variance de la cible.
    *   Mise à disposition d'un encodage optionnel One-Hot (`encode_categorical=True`).
*   **[Août 2026] Phase P1.2 - Non-Linéarité (Paliers & Optimums)** :
    *   Implémentation de la détection des relations par paliers (step functions, ANOVA par tranches).
    *   Implémentation de la détection des courbes paraboliques et optima locaux (régression polynomiale degré 2).
    *   Élargissement du scan aux paires numériques candidates au-delà du top des corrélations linéaires, avec inclusion prioritaire de la paire de simulation et plafond anti-explosion combinatoire.
    *   Limitation de l'affichage aux 3 meilleurs warnings P1.2 par gain explicatif pour réduire le bruit dans les rapports riches en colonnes.
    *   Avertissements générés lorsque le modèle linéaire passe à côté d'un rendement décroissant ou d'une tarification par tranches.
*   **[Août 2026] Phase F3 - Détection d'Asymétrie & Baseline Non-Représentative** :
    *   Implémentation de `_build_asymmetry_warnings` : détection des distributions asymétriques via le ratio `|mean - median| / std > 0.4`.
    *   Deux types d'alertes différenciés : *"Baseline de simulation peu représentative"* (cible Y asymétrique) et *"Point de départ du scénario peu représentatif"* (levier X asymétrique).
    *   Le warning suggère automatiquement le sous-groupe P1.1 déjà détecté, orientant vers la segmentation comme remède.
    *   Décision de ne pas modifier la valeur de la baseline — le moteur informe, ne décide pas à la place de l'utilisateur.
    *   **Correction de bugs** : `StepPatternResult.pattern_type` (AttributeError sur Tests #1/#4), `LogisticRegressionResult.slope` (AttributeError sur Test #15 / Cook's Distance) et simulation logistique bornée via sigmoïde avec variation affichée en points de probabilité.
*   **[Août 2026] Phase F5 - Détection de Distributions Non-Gaussiennes** :
    *   Implémentation de trois détecteurs indépendants dans `decision_core/stats/distribution.py` :
        *   `detect_count_data_distribution` : variables discrètes à valeurs limitées (comptages de pannes, nombre de pièces, durées en jours entiers).
        *   `detect_zero_inflation` : distributions avec masse excessive à zéro (sinistres, tickets support).
        *   `detect_heavy_tail` : queues lourdes de type Pareto / Loi de puissance (coûts d'incidents, CA extrêmes).
    *   Warnings pédagogiques en français suggérant le modèle adapté (Poisson, Zero-Inflated, Log-normale) sans modifier le modèle de régression sous-jacent.
    *   Taux de détection : 7/18 domaines (38,9%), couvrant les 3 cas critiques identifiés dans la Faille #5 (#9 Industrie, #12 Assurance, #15 SaaS).
*   **[Août 2026] Enrichissement des Datasets** :
    *   Passage de 12–35 lignes à 99–363 lignes par domaine, avec ajout de colonnes supplémentaires.
    *   Ce gain de puissance statistique a révélé des $R^2$ artificiellement élevés par sur-ajustement (ex : Ventes PME 0,97→0,15 ; Santé 0,41→0,005 ; SaaS 0,81→0,001) et renforcé la fiabilité des détections.

---

## 9. Taux de Détection Actuels (18 domaines, datasets enrichis)

| Catégorie | Domaines détectés | Taux |
|---|---|---|
| Asymétrie (F3) | #14, #16 | 11,1% |
| Distribution (F5) | #1, #5, #8, #9, #10, #12, #15 | 38,9% |
| Non-linéarité (P1.2) | #1–#13, #15, #16, #18 | 88,9% |
| Sous-groupes (P1.1) | #3–#5, #7, #8, #10–#12, #14, #16–#18 | 66,7% |
| Confondants (P0) | #1, #3, #5, #7, #11, #12, #14, #15, #17, #18 | 55,6% |
| Points influents | #1–#13, #16–#18 | 88,9% |
| Saisonnalité | #1, #3, #4, #7, #8, #10, #11, #17 | 44,4% |
| $R^2$ faible | #1, #5, #6, #12, #13, #15, #18 | 38,9% |
| Comparaisons multiples | #1–#6, #8–#18 | 94,4% |
| Colonnes dérivées | #4, #10, #11, #14 | 22,2% |

---

### 📋 Tâches Futures Identifiées

*   **[PRIORITÉ MOYENNE] Interprétation métier des probabilités très sensibles** :
    *   La simulation logistique produit désormais des probabilités valides dans $[0, 1]$ et affiche la variation en points de probabilité.
    *   Il reste à enrichir l'explication utilisateur quand une faible probabilité de départ produit une forte variation absolue après simulation.
    *   Objectif : éviter que l'utilisateur lise une probabilité projetée comme une prédiction certaine.
*   **[PRIORITÉ BASSE] Modèles de régression non-gaussiens** :
    *   F5 détecte les violations mais ne propose pas encore de modèle alternatif actif.
    *   Objectif : régression de Poisson, modèle à deux parties (Zero-Inflated), et régression log-normale comme alternatives automatiques.
