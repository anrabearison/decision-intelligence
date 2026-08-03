# Rapport d'Expérimentation et d'Analyse Inter-Domaines — decision-core

**Projet** : Decision Intelligence Engine  
**Composants analysés** : `decision-core` & `decision-engine`  
**Date d'expérimentation** : Août 2026  
**Nombre de domaines testés** : 15  

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

---

## 3. Détail des Rapports d'Analyse par Domaine

### Test 1 : Ventes PME & Retail
* **Fichier de test** : `examples/ventes_magasin_2025.csv`
* **Configuration de simulation** : Target = `Chiffre_Affaires`, Feature = `Budget_Pub`, Change % = `+10%`
* **Résultat obtenu** : Baseline = 2 261,85 €, Simulation = 2 412,60 € (+6,66%), $R^2 = 0,972$.
* **Analyse & Critique Métier** :
  - **Faux positifs sur les promotions** : Les remises de 5% et 10% sur la colonne `Remise_Pct` sont qualifiées d'anomalies IQR faussant les moyennes. C'est une fausse alerte pour un commerçant.
  - **Absence de segmentation** : La baseline globale (2 261 €) agrège sans distinction les magasins de PACA (1 200 €) et du Nord (3 500 €).
  - **Ignorance de la région** : La colonne texte `Region` est exclue des corrélations.

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
  - **Paradoxe de Simpson ($R = -0.884$)** : Le moteur conclut que plus la vache est lourde, moins son lait est riche. C'est simplement que les Jersey (petites) font du lait très gras et les Holstein (lourdes) du lait moins gras. Mélanger les deux races produit une conclusion biologiquement absurde.

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
  - **$R^2$ dérisoire (5%)** : Le temps dépend du `Mode_Livraison` (Express en 18h vs Relais en 48h), pas de la distance. Ignorer la colonne texte du mode de livraison rend la simulation inutile.
  - **Tarifs par paliers** : Les frais de port fonctionnent par tranches de poids fixes, inaccessibles à la régression linéaire.

### Test 6 : Santé & Suivi Clinique
* **Fichier de test** : `examples/sante_clinique_2025.csv`
* **Configuration de simulation** : Target = `Score_Retablissement`, Feature = `Dosage_Medicament_Mg`, Change % = `+50%`
* **Résultat obtenu** : Baseline = 80,47, Simulation = 75,34 (-6,37%), $R^2 = 0,413$.
* **Analyse & Critique Métier** :
  - **Biais d'Indication Médical** : Le moteur prédit qu'augmenter le dosage dégrade la santé des patients ! C'est simplement que les cas les plus graves reçoivent des doses plus fortes. Un médecin suivant ce conseil commettrait une erreur grave.

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
  - **Facteur Quartier ignoré** : Le m² au Centre vaut 6 000 € vs 2 500 € en Périphérie. Ne pas segmenter par `Quartier` fait chuter le $R^2$ à 0,42.

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
  - **Canal de réservation ignoré** : La corrélation géante (0,976) s'explique par les centrales Booking/Expedia réservées longtemps à l'avance et plus annulées que le direct.

### Test 11 : Restauration & Gastronomie
* **Fichier de test** : `examples/restauration_gastronomie_2025.csv`
* **Configuration de simulation** : Target = `Chiffre_Affaires_Jour`, Feature = `Nombre_Couverts`, Change % = `+20%`
* **Résultat obtenu** : Baseline = 2 396,93 €, Simulation = 2 876,32 € (+20,00%), $R^2 = 0,996$.
* **Analyse & Critique Métier** :
  - **Effet Weekend et Météo ignorés** : L'affluence dépend du `Jour_Semaine` et de la `Meteo` (variables texte non lues).

### Test 12 : Assurance & Sinistralité
* **Fichier de test** : `examples/assurance_sinistres_2025.csv`
* **Configuration de simulation** : Target = `Cout_Indemnisation_Euros`, Feature = `Puissance_Vehicule_CV`, Change % = `+15%`
* **Résultat obtenu** : Baseline = 3 393,33 €, Simulation = 4 580,20 € (+34,98%), $R^2 = 0,482$.
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
* **Résultat obtenu** : Baseline = 0,267 (26.7%), Simulation = 0,479 (47.9%), $R^2 = 0,643$.
* **Analyse & Critique Métier** :
  - **Cible binaire (Churn 0/1)** : Événement binaire estimé par régression linéaire ordinaire au lieu d'une régression logistique.

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

---

## 5. Recommandations d'Évolution pour decision-core

1. **Prise en compte des sous-groupes (Variables Catégorielles)** : Permettre au moteur de grouper les analyses par sous-groupes (`group_by` automatique par catégorie), ce qui éliminera 80% des pièges de Simpson et de confondateurs.
2. **Régression Logistique pour cibles binaires (0/1)** : Détecter les colonnes cibles à deux valeurs (ex: Churn, Panne, Guéri) et basculer sur une régression logistique avec bornes [0, 1].
3. **Planchers et Plafonds (Bornes)** : Permettre au moteur de borner les prédictions selon les min/max physiques ou institutionnels du dataset (ex: note de 0 à 20).
4. **Baseline basée sur la dernière valeur connue** : Utiliser la valeur récente du client plutôt que la moyenne historique globale de la colonne.
