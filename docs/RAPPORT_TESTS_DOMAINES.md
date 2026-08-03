# Rapport d'Expérimentation et d'Analyse Inter-Domaines — decision-core

**Projet** : Decision Intelligence Engine  
**Composants analysés** : `decision-core` & `decision-engine`  
**Date d'expérimentation** : Août 2026  
**Nombre de domaines testés** : 18  

---

## 1. Présentation et Objectifs

Ce document présente l'évaluation expérimentale menée sur le moteur `decision-core` à travers **15 jeux de données réels et synthétiques** couvrant des secteurs d'activité variés. 

L'objectif de cette campagne d'expérimentation est de confronter les algorithmes de `decision-core` (importer locale-aware, détection de type, détection de colonnes dérivées, profilage, corrélations corrigées Benjamini-Hochberg, détection d'anomalies IQR, points influents de Cook, et régression/simulation) à la réalité métier de chaque secteur.

---

## 2. Inventaire des 15 Fichiers de Test

Tous les fichiers CSV ci-dessous sont enregistrés dans le répertoire `decision-core/examples/` et peuvent être ré-exécutés avec le script d'analyse :

| N° | Domaine | Nom du Fichier CSV | Délimiteur / Décimale | Nombre de Lignes |
|---|---|---|---|---|
| 1 | **Ventes PME / Retail** | `examples/ventes_magasin_2025.csv` | `;` / `,` | 35 |
| 2 | **Ressources Humaines** | `examples/rh_masse_salariale_2025.csv` | `;` / `,` | 20 |
| 3 | **Élevage / Agriculture** | `examples/elevage_production_lait_2025.csv` | `;` / `,` | 15 |
| 4 | **Finance / Trésorerie** | `examples/finance_tresorerie_2025.csv` | `;` / `,` | 12 |
| 5 | **Logistique / E-Commerce** | `examples/logistique_livraisons_2025.csv` | `;` / `,` | 15 |
| 6 | **Santé / Clinique** | `examples/sante_clinique_2025.csv` | `;` / `,` | 15 |
| 7 | **Éducation / E-Learning** | `examples/education_elearning_2025.csv` | `;` / `,` | 15 |
| 8 | **Immobilier** | `examples/immobilier_estimations_2025.csv` | `;` / `,` | 15 |
| 9 | **Industrie / Maintenance** | `examples/industrie_maintenance_2025.csv` | `;` / `,` | 15 |
| 10 | **Hôtellerie / Booking** | `examples/hotellerie_reservations_2025.csv` | `;` / `,` | 15 |
| 11 | **Restauration** | `examples/restauration_gastronomie_2025.csv` | `;` / `,` | 14 |
| 12 | **Assurance & Sinistres** | `examples/assurance_sinistres_2025.csv` | `;` / `,` | 15 |
| 13 | **Énergie Bâtiments** | `examples/energie_batiments_2025.csv` | `;` / `,` | 15 |
| 14 | **Marketing Digital** | `examples/marketing_digital_2025.csv` | `;` / `,` | 15 |
| 15 | **SaaS Abonnements** | `examples/saas_abonnements_2025.csv` | `;` / `,` | 15 |
| 16 | **Cybersécurité / IT** | `examples/cybersecurite_incidents_2025.csv` | `;` / `,` | 15 |
| 17 | **Tourisme / Culture** | `examples/tourisme_frequentation_2025.csv` | `;` / `,` | 15 |
| 18 | **Agriculture / Céréales** | `examples/agriculture_rendement_2025.csv` | `;` / `,` | 15 |

---

## 3. Détail des Rapports d'Analyse par Domaine

### Test 1 : Ventes PME & Retail
* **Fichier de test** : `examples/ventes_magasin_2025.csv`
* **Configuration de simulation** : Target = `Chiffre_Affaires`, Feature = `Budget_Pub`, Change % = `+10%`
* **Résultat obtenu** : Baseline = 2 261,85 €, Simulation = 2 412,60 € (+6,66%), $R^2 = 0,972$.
* **Analyse & Critique Métier** :
  - **Faux positifs sur les promotions** : Les remises de 5% et 10% sur la colonne `Remise_Pct` sont qualifiées d'anomalies IQR faussant les moyennes. C'est une fausse alerte pour un commerçant.
  - ~~**Absence de segmentation** : La baseline globale (2 261 €) agrège sans distinction les magasins de PACA (1 200 €) et du Nord (3 500 €).~~
  - ~~**Ignorance de la région** : La colonne texte `Region` est exclue des corrélations.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : La colonne `Region` est maintenant intégrée via un encodage One-Hot optionnel et détectée comme sous-groupe majeur, ce qui permet d'orienter vers une résolution du problème de la baseline globale.</span>

### Test 2 : Ressources Humaines
* **Fichier de test** : `examples/rh_masse_salariale_2025.csv`
* **Configuration de simulation** : Target = `Salaire_Brut_Mensuel`, Feature = `Anciennete_Annees`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 4 252,53 €, Simulation = 4 509,37 € (+6,04%), $R^2 = 0,739$.
* **Analyse & Critique Métier** :
  - **Facteur confondant du département** : Corrélation `Formation_Jours ↔ Salaire` (0.734) due au fait que la Tech gagne plus ET se forme plus que les RH.
  - **Rampe linéaire irréaliste** : En RH, les augmentations se font par paliers et grilles salariales, pas via une droite linéaire continue.

### Test 3 : Élevage & Agriculture
* **Fichier de test** : `examples/elevage_production_lait_2025.csv`
* **Configuration de simulation** : Target = `Litres_Lait_Jour`, Feature = `Ration_Fourrage_Kg`, Change % = `+15%`
* **Résultat obtenu** : Baseline = 26,30 L, Simulation = 30,92 L (+17,57%), $R^2 = 0,830$.
* **Analyse & Critique Métier** :
  - ~~**Paradoxe de Simpson ($R = -0.884$)** : Le moteur conclut que plus la vache est lourde, moins son lait est riche. C'est simplement que les Jersey (petites) font du lait très gras et les Holstein (lourdes) du lait moins gras. Mélanger les deux races produit une conclusion biologiquement absurde.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0/P1.1)** : Le moteur identifie désormais la `Race` comme sous-groupe significatif ($\eta^2$) et lève une alerte explicite de corrélation spurieuse pour alerter l'utilisateur du biais de causalité.</span>

### Test 4 : Finance & Trésorerie PME
* **Fichier de test** : `examples/finance_tresorerie_2025.csv`
* **Configuration de simulation** : Target = `Solde_Tresorerie_Euros`, Feature = `Delai_Paiement_Jours`, Change % = `-20%`
* **Résultat obtenu** : Baseline = 39 166,67 €, Simulation = 66 299,44 € (+69,28%), $R^2 = 0,894$.
* **Analyse & Critique Métier** :
  - **Succès arithmétique** : `derived_columns.py` a bien retiré la relation `Créances + Dettes = Trésorerie`.
  - **Surestimation massive** : Projette une hausse de trésorerie de +69% car le modèle attribue l'impact de deux mois d'achats d'équipements exceptionnels (Investissements) au seul délai de paiement.

### Test 5 : Logistique & Livraisons E-Commerce
* **Fichier de test** : `examples/logistique_livraisons_2025.csv`
* **Configuration de simulation** : Target = `Temps_Livraison_Heures`, Feature = `Distance_Km`, Change % = `+10%`
* **Résultat obtenu** : Baseline = 44,40 h, Simulation = 45,07 h (+1,51%), $R^2 = 0,053$ (Échec).
* **Analyse & Critique Métier** :
  - ~~**$R^2$ dérisoire (5%)** : Le temps dépend du `Mode_Livraison` (Express en 18h vs Relais en 48h), pas de la distance. Ignorer la colonne texte du mode de livraison rend la simulation inutile.~~
  - **Tarifs par paliers** : Les frais de port fonctionnent par tranches de poids fixes, inaccessibles à la régression linéaire.
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : Le moteur identifie désormais `Mode_Livraison` comme le sous-groupe principal ($\eta^2$) déterminant le temps de livraison.</span>

### Test 6 : Santé & Suivi Clinique
* **Fichier de test** : `examples/sante_clinique_2025.csv`
* **Configuration de simulation** : Target = `Score_Retablissement`, Feature = `Dosage_Medicament_Mg`, Change % = `+50%`
* **Résultat obtenu** : Baseline = 80,47, Simulation = 75,34 (-6,37%), $R^2 = 0,413$.
* **Analyse & Critique Métier** :
  - ~~**Biais d'Indication Médical** : Le moteur prédit qu'augmenter le dosage dégrade la santé des patients ! C'est simplement que les cas les plus graves reçoivent des doses plus fortes. Un médecin suivant ce conseil commettrait une erreur grave.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0)** : La fonction `detect_confounders` identifie la sévérité initiale comme facteur confondant et génère un avertissement de corrélation spurieuse, empêchant l'erreur d'interprétation.</span>

### Test 7 : Éducation & E-Learning
* **Fichier de test** : `examples/education_elearning_2025.csv`
* **Configuration de simulation** : Target = `Note_Examen_Sur_20`, Feature = `Temps_Video_Heures`, Change % = `+30%`
* **Résultat obtenu** : Baseline = 15,67/20, Simulation = 17,57/20 (+12,15%), $R^2 = 0,890$.
* **Analyse & Critique Métier** :
  - **Dépassement du plafond (26/20)** : Sans bornes institutionnelles (0 à 20), la régression linéaire projette des notes > 20 pour un temps de révision élevé.

### Test 8 : Immobilier & Estimation de Biens
* **Fichier de test** : `examples/immobilier_estimations_2025.csv`
* **Configuration de simulation** : Target = `Prix_Vente_Euros`, Feature = `Surface_M2`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 340 666,67 €, Simulation = 395 254,62 € (+16,02%), $R^2 = 0,428$.
* **Analyse & Critique Métier** :
  - ~~**Facteur Quartier ignoré** : Le m² au Centre vaut 6 000 € vs 2 500 € en Périphérie. Ne pas segmenter par `Quartier` fait chuter le $R^2$ à 0,42.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : La variable `Quartier` est désormais détectée comme structurante, suggérant automatiquement à l'utilisateur de procéder à une analyse segmentée.</span>

### Test 9 : Industrie & Maintenance Prédictive
* **Fichier de test** : `examples/industrie_maintenance_2025.csv`
* **Configuration de simulation** : Target = `Anomalies_Comptees`, Feature = `Heures_Fonctionnement`, Change % = `+25%`
* **Résultat obtenu** : Baseline = 1,47, Simulation = 2,27 (+54,76%), $R^2 = 0,829$.
* **Analyse & Critique Métier** :
  - **Pannes de type Poisson** : Traiter des comptages discrets de pannes (0, 1, 2, 5) par régression gaussienne continue est théoriquement inadapté (besoin de modèles de Poisson/Weibull).

### Test 10 : Hôtellerie & Réservations
* **Fichier de test** : `examples/hotellerie_reservations_2025.csv`
* **Configuration de simulation** : Target = `Taux_Annulation_Pct`, Feature = `Delai_Reservation_Jours`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 9,82%, Simulation = 11,90% (+21,15%), $R^2 = 0,954$.
* **Analyse & Critique Métier** :
  - ~~**Canal de réservation ignoré** : La corrélation géante (0,976) s'explique par les centrales Booking/Expedia réservées longtemps à l'avance et plus annulées que le direct.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0/P1.1)** : Le moteur alerte sur la corrélation spurieuse et détecte le canal d'acquisition comme facteur confondant et sous-groupe essentiel.</span>

### Test 11 : Restauration & Gastronomie
* **Fichier de test** : `examples/restauration_gastronomie_2025.csv`
* **Configuration de simulation** : Target = `Chiffre_Affaires_Jour`, Feature = `Nombre_Couverts`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 2 528,82 €, Simulation = 3 208,82 € (+26,89%), $R^2 = 0,995$.
* **Analyse & Critique Métier** :
  - **Effet Weekend et Météo ignorés** : L'affluence dépend du `Jour_Semaine` et de la `Meteo` (variables texte non lues).

### Test 12 : Assurance & Sinistralité
* **Fichier de test** : `examples/assurance_sinistres_2025.csv`
* **Configuration de simulation** : Target = `Cout_Indemnisation_Euros`, Feature = `Puissance_Vehicule_CV`, Change % = `+15%`
* **Résultat obtenu** : Baseline = 3 393,33 €, Simulation = 5 286,67 € (+55,80%), $R^2 = 0,298$.
* **Analyse & Critique Métier** :
  - **Distribution Zéro-Inflated** : 75% des assurés ont 0 € de sinistre. Une régression linéaire produit un coût moyen fictif sans utilité actuarielle.

### Test 13 : Énergie & Consommation Bâtiments
* **Fichier de test** : `examples/energie_batiments_2025.csv`
* **Configuration de simulation** : Target = `Consommation_KWh`, Feature = `Temperature_Exterieure_C`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 3 586,67 kWh, Simulation = 3 173,95 kWh (-11,51%), $R^2 = 0,627$.
* **Analyse & Critique Métier** :
  - **Courbe en U (Climatisation)** : La consommation monte en hiver (Chauffage) et remonte en été (Climatisation). Le modèle linéaire rate le creux parabolique.

### Test 14 : Marketing Digital & SEO/Adwords
* **Fichier de test** : `examples/marketing_digital_2025.csv`
* **Configuration de simulation** : Target = `Cout_Acquisition_CAC`, Feature = `Cout_Par_Clic_CPC`, Change % = `+10%`
* **Résultat obtenu** : Baseline = 103,04 €, Simulation = 115,35 € (+11,95%), $R^2 = 0,970$.
* **Analyse & Critique Métier** :
  - **Mélange de réseaux hétérogènes** : Agrège LinkedIn (CPC 4.50€) et Facebook (CPC 0.60€) sans distinction du canal publicitaire.

### Test 15 : SaaS & Abonnements (Churn)
* **Fichier de test** : `examples/saas_abonnements_2025.csv`
* **Configuration de simulation** : Target = `Desabonnement_Churn`, Feature = `Tickets_Support`, Change % = `+50%`
* **Résultat obtenu** : Baseline = 0,267 (26.7%), Simulation = 0,479 (47.9%) soit +79,45% relatif, $R^2 = 0,643$.
* **Analyse & Critique Métier** :
  - ~~**Cible binaire (Churn 0/1)** : Événement binaire estimé par régression linéaire ordinaire au lieu d'une régression logistique.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0)** : Le moteur détecte automatiquement les cibles binaires et bascule sur une régression logistique (L-BFGS-B). Les probabilités sont correctement bornées dans $[0, 1]$.</span>

---

## 4. Tableau de Synthèse Finale des 15 Domaines

| N° | Domaine | Fichier CSV | Verdict | Limite Métier Majeure Découverte |
|---|---|---|---|---|
| 1 | **Ventes PME** | `examples/ventes_magasin_2025.csv` | ⚠️ Utile mais réducteur | Faux alerte IQR sur remises promo ; baseline moyenne globale. |
| 2 | **RH** | `examples/rh_masse_salariale_2025.csv` | ⚠️ Risqué | Biais du département ; rampe linéaire irréaliste sur grilles salariales. |
| 3 | **Élevage** | `examples/elevage_production_lait_2025.csv` | ❌ Dangereux | **Paradoxe de Simpson** ($R = -0.88$) par non-segmentation des races. |
| 4 | **Finance** | `examples/finance_tresorerie_2025.csv` | ⚠️ Surestimé | Formules comptables OK, mais surestimation (+69%) via flux d'investissement. |
| 5 | **Logistique** | `examples/logistique_livraisons_2025.csv` | ❌ Échec ($R^2=0,05$) | Incapacité à modéliser Express vs Relais et tarification par tranches. |
| 6 | **Santé** | `examples/sante_clinique_2025.csv` | ❌ Dangereux | **Biais d'Indication** : conclusion que le médicament dégrade la santé. |
| 7 | **Éducation** | `examples/education_elearning_2025.csv` | ⚠️ Abstrait | Projections hors bornes (note > 20/20) et ignorance du rendement décroissant. |
| 8 | **Immobilier** | `examples/immobilier_estimations_2025.csv` | ⚠️ Médiocre ($R^2=0,42$) | Emplacement (Quartier) ignoré sur la valeur au m². |
| 9 | **Industrie** | `examples/industrie_maintenance_2025.csv` | ⚠️ Inadapté | Régression linéaire appliquée à des comptages de pannes (Poisson). |
| 10 | **Hôtellerie** | `examples/hotellerie_reservations_2025.csv` | ⚠️ Partiel | Canal d'acquisition (Booking/Direct) ignoré sur les annulations. |
| 11 | **Restauration**| `examples/restauration_gastronomie_2025.csv`| ⚠️ Incomplet | Effets du weekend et de la météo ignorés. |
| 12 | **Assurance** | `examples/assurance_sinistres_2025.csv` | ❌ Inadapté | Distribution à zéro gonflé (90% à 0 €) traitée en moyenne linéaire. |
| 13 | **Énergie** | `examples/energie_batiments_2025.csv` | ❌ Inadapté | Courbe en U (chauffage hiver vs clim été) invisible en régression simple. |
| 14 | **Marketing Digital** | `examples/marketing_digital_2025.csv` | ⚠️ Mélangé | Agrégation aveugle de canaux publicitaires hétérogènes (Google vs LinkedIn). |
| 15 | **SaaS Abonnements** | `examples/saas_abonnements_2025.csv` | ⚠️ Incomplet | Événement binaire de Churn (0/1) estimé par régression linéaire ordinaire au lieu de logistique. |
| 16 | **Cybersécurité** | `examples/cybersecurite_incidents_2025.csv` | ❌ Inadapté | Distribution Pareto extrême ; sévérité de l'incident (variable texte) ignorée. |
| 17 | **Tourisme** | `examples/tourisme_frequentation_2025.csv` | ❌ Dangereux | Inversion de causalité : hausse de prix corrélée à la fréquentation (saisonnalité ignorée). |
| 18 | **Agriculture** | `examples/agriculture_rendement_2025.csv` | ❌ Échec ($R^2=0,0003$) | Relation en courbe gaussienne (optimum de pluie) impossible à capter avec une droite linéaire. |

---

## 6. Matrice de Correspondance : Critiques Fusionnées ↔ Tests CSV Réels

Ce tableau démontre comment **chaque critique identifiée dans l'audit** est directement illustrée et prouvée par un ou plusieurs des 15 tests CSV du projet :

| Critique Identifiée dans l'Audit | Fichier CSV de Démonstration | Manifestation Concrète observée |
|---|---|---|
| **1. Ignorance des catégories / sous-groupes (Variables texte)** | `examples/elevage_production_lait_2025.csv`<br>`examples/rh_masse_salariale_2025.csv`<br>`examples/immobilier_estimations_2025.csv` | **Paradoxe de Simpson** ($R=-0,88$ entre Poids et Gras du lait par mélange des races Holstein/Jersey).<br>Confondateur `Departement` en RH.<br>`Quartier` ignoré en immobilier. |
| **2. Biais de causalité & Biais d'Indication** | `examples/sante_clinique_2025.csv`<br>`examples/finance_tresorerie_2025.csv`<br>`examples/hotellerie_reservations_2025.csv` | Prédiction qu'augmenter la dose de médicament dégrade le rétablissement (patients plus graves dosés plus fort).<br>Attribution de l'effet d'investissements au seul délai de paiement. |
| **3. Baseline sur la moyenne (pas la valeur récente)** | `examples/ventes_magasin_2025.csv`<br>`examples/restauration_gastronomie_2025.csv` | Baseline à 2 261 € qui ne correspond ni au Nord (3 500 €) ni à PACA (1 200 €).<br>Moyenne qui agrège les weekends et les jours de semaine. |
| **4. Incapacité à modéliser des bornes (Notes / Plafonds)** | `examples/education_elearning_2025.csv` | Extrapolation linéaire prédisant des notes de **26/20** au-delà de 80h d'étude. |
| **5. Aveuglement aux courbes en U (Non-linéarité)** | `examples/energie_batiments_2025.csv` | Modèle linéaire unable de capter le creux de consommation (Chauffage l'hiver + Climatisation l'été). |
| **6. Régression linéaire sur événement binaire (0/1)** | `examples/saas_abonnements_2025.csv` | Prédiction de Churn (0 ou 1) via une droite continue au lieu d'une régression logistique. |
| **7. Distribution Zéro-Inflated (Sinistres)** | `examples/assurance_sinistres_2025.csv` | Coût moyen théorique appliqué sur une population où 75% des personnes ont 0 € de sinistre. |
| **8. Incompatibilité avec les tarifications par paliers** | `examples/logistique_livraisons_2025.csv` | Effondrement du modèle ($R^2=0,05$) sur des livraisons à tarifs par tranches de poids fixe. |
| **9. Régression continue sur comptages discrets** | `examples/industrie_maintenance_2025.csv` | Modèle gaussien appliqué à des nombres entiers d'anomalies (besoin de loi de Poisson/Weibull). |
| **10. Faux positifs sur les alertes métiers** | `examples/ventes_magasin_2025.csv` | Promotions normales de 5% et 10% qualifiées d'*"anomalies IQR à vérifier"*. |

### Test 16 : Cybersécurité & Incidents IT
* **Fichier de test** : `examples/cybersecurite_incidents_2025.csv`
* **Configuration de simulation** : Target = `Cout_Incident_Euros`, Feature = `Nb_Systemes_Touches`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 167 993 €, Simulation = 217 809 € (+29,65%), $R^2 = 0,914$.
* **Analyse & Critique Métier** :
  - **Distribution bimodale extrême (Pareto / Loi de puissance)** : 80% des incidents coûtent moins de 22 000 €, mais 3 incidents critiques (`Critique`) coûtent entre 280 000 € et 950 000 €. La régression linéaire produit une baseline à 167 993 € qui ne correspond à aucune catégorie réelle.
  - ~~**La sévérité de l'incident (`Criticite`) est ignorée** : C'est la variable texte `Criticite` (Faible / Moyen / Critique) qui explique 95% du coût. Le moteur ne peut pas l'intégrer.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : Le moteur identifie désormais `Criticite` comme sous-groupe majeur expliquant près de 87% de la variance des coûts.</span>

### Test 17 : Tourisme & Fréquentation Culturelle
* **Fichier de test** : `examples/tourisme_frequentation_2025.csv`
* **Configuration de simulation** : Target = `Visiteurs_Jour`, Feature = `Prix_Billet_Euros`, Change % = `-10%`
* **Résultat obtenu** : Baseline = 971 visiteurs/jour, Simulation = 589 visiteurs/jour (-39,27%), $R^2 = 0,470$.
* **Analyse & Critique Métier** :
  - ~~**Inversion de causalité** : Le moteur conclut qu'une baisse de prix de 10% ferait chuter les visiteurs de 39% ! En réalité, le prix élevé (16 €) correspond à l'été (haute saison) avec 2 800 visiteurs. C'est la saison qui explique les deux variables — le musée augmente ses prix en haute saison.~~
  - ~~**Les vraies variables sont ignorées** : `Saison` et `Vacances_Scolaires` (colonnes texte booléen) expliquent bien mieux la fréquentation que le prix du billet.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P0/P1.1)** : Le moteur alerte formellement sur la corrélation spurieuse causée par `Saison` et détecte ces colonnes catégorielles comme des sous-groupes significatifs à analyser séparément.</span>

### Test 18 : Agriculture & Rendement Céréalier
* **Fichier de test** : `examples/agriculture_rendement_2025.csv`
* **Configuration de simulation** : Target = `Rendement_Quintal_Ha`, Feature = `Pluviometrie_Mm`, Change % = `+15%`
* **Résultat obtenu** : Baseline = 56,80 q/ha, Simulation = 56,90 q/ha (+0,18%), $R^2 = 0,0003$ (Effondrement total).
* **Analyse & Critique Métier** :
  - **Effondrement complet du modèle ($R^2 = 0,0003$)** : La pluviométrie n'explique que 0,03% du rendement selon le modèle. Résultat en réalité attendu par un agronome.
  - **Relation en courbe de Gauss (Optimum de pluviométrie)** : Trop peu de pluie (150 mm → sécheresse) ET trop de pluie (620 mm → noyade des cultures) réduisent le rendement. Le meilleur rendement se situe entre 280 et 400 mm. Une droite linéaire est aveugle à cet optimum parabolicique.
  - ~~**Le Type de sol est ignoré** : Le Limon produit 72 q/ha tandis que le Sable produit 40 q/ha à pluviométrie équivalente. La colonne texte `Type_Sol` est la variable déterminante non prise en compte.~~
* <span style="color: #2ea043;">**État Actuel (Août 2026 - Phase P1.1)** : Le moteur détecte désormais que `Type_Sol` est responsable de 88% de la variance du rendement et avertit l'utilisateur. La non-linéarité (courbe gaussienne) reste à traiter (Phase P1.2).</span>

---

## 5. Analyse des Répétitions de Critiques

Sur les 18 tests réalisés, l'analyse transversale révèle que **les critiques ne sont pas indépendantes**. Elles se regroupent en **5 failles structurelles** qui se manifestent répétitivement sous des formes sectorielles différentes.

> **Conclusion clé** : Ce ne sont pas 18 problèmes distincts — c'est le même ensemble de 5 limites architecturales qui se répète. Corriger ces 5 points résoudrait l'essentiel de la surface de risque du moteur.

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
| #18 Agriculture | `Type_Sol` | 40% de variance du rendement inexpliquée |

---

### Faille #2 — Inversion de causalité / Facteur confondant *(4 tests sur 18)*

Le moteur confond une corrélation spurieuse avec une relation de cause à effet, conduisant à des recommandations opérationnelles incorrectes, voire dangereuses.

| Test | Corrélation spurieuse détectée | Vrai facteur confondant caché |
|---|---|---|
| #3 Élevage | Poids ↔ Taux de gras du lait ($R=-0,88$) | Race (Holstein légères vs Jersey lourdes) |
| #6 Santé | Dosage ↔ Dégradation de la santé | Sévérité initiale du patient (biais d'indication) |
| #10 Hôtellerie | Délai de réservation ↔ Annulation | Canal d'acquisition (Booking vs Direct) |
| #17 Tourisme | Prix du billet ↔ Fréquentation | Saison (prix hauts ET visiteurs hauts en été) |

---

### Faille #3 — Baseline = moyenne globale sans sens métier *(3 tests sur 18)*

La baseline calculée comme moyenne arithmétique de l'historique complet ne correspond à aucune situation concrète exploitable par un décideur.

| Test | Baseline calculée | Problème métier |
|---|---|---|
| #1 Ventes PME | 2 261 €/transaction | Ni région Nord (3 500 €) ni PACA (1 200 €) |
| #11 Restauration | 2 397 €/jour | Mélange weekends (haute affluence) + semaine |
| #16 Cybersécurité | 167 993 € par incident | Aucun incident à ce coût : soit < 22 000 € soit > 280 000 € |

---

### Faille #4 — Non-linéarité ignorée (courbe en U / paliers / optimum) *(3 tests sur 18)*

Le moteur applique systématiquement une droite linéaire, aveugle à toute relation en courbe, seuil ou optimum.

| Test | Type de non-linéarité réelle |
|---|---|
| #5 Logistique | Tarification par paliers de poids (escaliers, pas une droite) |
| #13 Énergie | Courbe en U : Chauffage (hiver) + Climatisation (été), creux au printemps |
| #18 Agriculture | Optimum gaussien de pluviométrie (300-400 mm) : trop sec ET trop humide = mauvais rendement |

---

### Faille #5 — Distribution non-gaussienne traitée comme normale *(3 tests sur 18)*

Le moteur de régression suppose implicitement une distribution gaussienne (loi normale). Cette hypothèse est incorrecte pour les données de comptage, les sinistres rares et les incidents à loi de puissance.

| Test | Distribution réelle | Modèle adapté manquant |
|---|---|---|
| #9 Industrie | Comptages discrets (0, 1, 2, 5 pannes) | Régression de Poisson / Weibull |
| #12 Assurance | Zéro-Inflated (75% à 0 € de sinistre) | Modèle à deux parties (Zero-Inflated) |
| #16 Cybersécurité | Pareto / Loi de puissance (3 incidents = 95% des coûts) | Log-normale ou modèle de mélange |

---

### Carte de chaleur des failles par test

| Test | F1 Catégories | F2 Causalité | F3 Baseline | F4 Non-linéarité | F5 Distribution |
|---|:---:|:---:|:---:|:---:|:---:|
| #1 Ventes PME | ✅ | | ✅ | | |
| #2 RH | ✅ | ✅ | | | |
| #3 Élevage | ✅ | ✅ | | | |
| #4 Finance | | ✅ | | | |
| #5 Logistique | ✅ | | | ✅ | |
| #6 Santé | | ✅ | | | |
| #7 Éducation | | | | ✅ | |
| #8 Immobilier | ✅ | | | | |
| #9 Industrie | | | | | ✅ |
| #10 Hôtellerie | ✅ | ✅ | | | |
| #11 Restauration | ✅ | | ✅ | | |
| #12 Assurance | | | | | ✅ |
| #13 Énergie | | | | ✅ | |
| #14 Marketing | ✅ | | | | |
| #15 SaaS | | | | | ✅ |
| #16 Cybersécurité | ✅ | | ✅ | | ✅ |
| #17 Tourisme | ✅ | ✅ | | | |
| #18 Agriculture | ✅ | | | ✅ | |
| **Total** | **9** | **6** | **3** | **4** | **4** |

---

## 6. Recommandations d'Évolution pour decision-core

1. **Prise en compte des sous-groupes (Variables Catégorielles)** : Permettre au moteur de grouper les analyses par sous-groupes (`group_by` automatique par catégorie), ce qui éliminera 80% des pièges de Simpson et de confondateurs.
2. **Régression Logistique pour cibles binaires (0/1)** : Détecter les colonnes cibles à deux valeurs (ex: Churn, Panne, Guéri) et basculer sur une régression logistique avec bornes [0, 1].
3. **Planchers et Plafonds (Bornes)** : Permettre au moteur de borner les prédictions selon les min/max physiques ou institutionnels du dataset (ex: note de 0 à 20).
4. **Baseline basée sur la dernière valeur connue** : Utiliser la valeur récente du client plutôt que la moyenne historique globale de la colonne.

---

## 7. Historique des Résolutions

*   **[Août 2026] Phase P0 - Régression Logistique & Causalité** : 
    *   Implémentation de `fit_logistic_regression` (via `scipy.optimize.minimize` L-BFGS-B) pour les cibles binaires avec bornage naturel $[0, 1]$.
    *   Ajout de la détection systématique des biais de causalité (`detect_confounders`) et d'avertissements explicites de corrélation spurieuse.
*   **[Août 2026] Phase P1.1 - Variables Catégorielles** :
    *   Ajout de la détection des sous-groupes structurants via l'analyse de la variance ($\eta^2$). Le moteur avertit désormais quand une variable catégorielle explique une forte variance de la cible.
    *   Mise à disposition d'un encodage optionnel One-Hot (`encode_categorical=True`).
