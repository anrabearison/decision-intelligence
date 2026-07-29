# Decision Intelligence Engine — Spécification fonctionnelle

**Périmètre** : Phase 1a (moteur) + Phase 2 (interface), état actuel du produit.
Ce document décrit *ce que fait le produit du point de vue de l'utilisateur* — pour l'architecture technique, voir `SPEC.md`.

---

## 1. Objet du produit

Un outil qui permet à une personne non-spécialiste des statistiques d'importer un fichier de données (ventes, élevage, RH, finances...) et d'obtenir automatiquement :
- une lecture fiable de ce que contiennent ses données,
- les relations les plus pertinentes entre ses variables,
- une estimation chiffrée de l'effet d'un changement qu'elle envisage.

Le produit ne remplace pas un expert humain sur des décisions complexes ; il donne une base de lecture rigoureuse, plus fiable qu'un coup d'œil sur un tableur, sans demander de compétence technique.

## 2. À qui s'adresse le produit

- Une personne qui gère une activité (commerce, exploitation agricole, PME) et veut comprendre ses propres données sans les compétences pour le faire elle-même
- Une personne à l'aise avec les chiffres mais qui veut gagner du temps par rapport à une analyse manuelle
- **Explicitement pas ciblé** : quelqu'un qui maîtrise déjà bien un outil comme un chat IA générique pour ce type d'analyse — voir section 9.

## 3. Ce que l'utilisateur peut faire aujourd'hui (parcours)

### 3.1 Déposer un fichier
L'utilisateur glisse-dépose ou sélectionne un fichier CSV ou Excel contenant ses données (une ligne = une observation, une colonne = une variable).

### 3.2 Configurer une simulation (facultatif)
Avant de lancer l'analyse, l'utilisateur peut préciser :
- **une colonne cible** : ce qu'il veut estimer (ex : ses ventes)
- **une variable qu'il envisage de changer** (ex : le prix)
- **de combien il envisage de la changer, en %** (ex : +5%)

Cette étape est optionnelle. Sans elle, l'utilisateur obtient uniquement la lecture de ses données (étapes 3.3 à 3.5), sans estimation d'un changement.

### 3.3 Recevoir la structure de son fichier
Avant toute analyse, l'utilisateur voit :
- le nombre de lignes et de colonnes détectées
- le nombre de doublons trouvés
- le nombre de valeurs manquantes, colonne par colonne

### 3.4 Recevoir une lecture statistique de ses données
Pour chaque colonne numérique exploitable, l'utilisateur reçoit sa moyenne, son écart-type, sa médiane, son minimum et son maximum.

L'utilisateur reçoit les relations les plus fortes trouvées entre ses variables (les 5 plus marquantes), présentées avec deux informations : la force de la relation, et si elle est jugée suffisamment fiable statistiquement pour ne pas être due au hasard (voir section 7).

### 3.5 Recevoir une estimation chiffrée (si une simulation a été configurée)
L'utilisateur reçoit :
- la valeur actuelle de sa cible
- la valeur estimée après le changement envisagé
- la variation en pourcentage entre les deux — **sauf si cette variation n'est pas jugée fiable** (voir section 7), auquel cas seules les valeurs absolues sont montrées
- un indicateur de la fiabilité globale de cette estimation (R²)

### 3.6 Être averti des limites de sa propre analyse
À chaque étape, l'utilisateur peut recevoir des avertissements explicites plutôt qu'un résultat présenté comme certain. Voir la liste complète en section 7.

## 4. Formats de fichiers acceptés

| Accepté | Non accepté (Phase 1a) |
|---|---|
| CSV (virgule ou point-virgule) | Fichiers avec plusieurs feuilles Excel liées (une seule feuille lue) |
| Excel (.xlsx, .xls) | Jointure entre plusieurs fichiers |
| Encodage international (UTF-8) ou Windows français (CP1252) | Texte libre analysé sémantiquement (avis, commentaires) |
| Virgule décimale française (ex: `12,50`) | Images, PDF, audio |
| Valeurs manquantes en français (`N/D`, `NR`, etc.) et international (`N/A`, vide, `null`) | — |

**Taille maximale** : 50 Mo par fichier.

Si le fichier ne peut pas être lu de façon fiable (par exemple, un mélange de virgule décimale et de virgule de séparation qui rend le fichier ambigu), l'utilisateur reçoit un message clair expliquant pourquoi, plutôt qu'un résultat basé sur des données mal interprétées.

## 5. Ce que le produit calcule pour l'utilisateur

| Besoin utilisateur | Ce que le produit fournit |
|---|---|
| "Qu'est-ce qu'il y a dans mon fichier ?" | Structure, doublons, valeurs manquantes |
| "Quelles sont mes variables numériques et leurs ordres de grandeur ?" | Moyenne, écart-type, médiane, min, max par colonne |
| "Quelles variables sont liées entre elles chez moi ?" | Les relations les plus fortes, avec un indicateur de fiabilité statistique |
| "Et si je change X, qu'est-ce que ça donne sur Y ?" | Une estimation chiffrée, avec sa marge de confiance |
| "Est-ce que je peux faire confiance à ce résultat ?" | Des avertissements explicites chaque fois qu'une limite s'applique |

## 6. Ce que le produit ne fait pas (hors périmètre actuel)

- Il ne recommande pas une décision ("vous devriez faire X") — il donne des éléments chiffrés, la décision reste à l'utilisateur (une couche de recommandation est prévue en Phase 3, non disponible aujourd'hui)
- Il ne détecte pas de tendance dans le temps ni de saisonnalité
- Il n'estime pas de risque ni de probabilité de succès (prévu Phase 1b/3)
- Il ne corrige jamais automatiquement une donnée manquante ou aberrante — il la signale seulement, la décision de la traiter reste à l'utilisateur
- Il ne conserve pas l'historique des analyses d'un utilisateur (pas de compte, pas de connexion — prévu Phase 5)
- Il ne discute pas avec l'utilisateur en langage naturel (pas de chat — prévu Phase 4)

## 7. Avertissements que l'utilisateur peut recevoir, et ce qu'ils signifient

| Avertissement | Ce que ça veut dire concrètement pour l'utilisateur |
|---|---|
| Échantillon petit (dataset global) | Moins de 30 lignes au total : les résultats sont à prendre comme une indication, pas une certitude |
| Échantillon effectif réduit pour la simulation | Même avec un gros fichier, si beaucoup de valeurs sont manquantes sur les deux colonnes choisies pour la simulation, celle-ci repose en réalité sur peu de données |
| Confiance faible de l'estimation (R² faible) | Le changement envisagé (variable choisie) n'explique qu'une petite partie de ce qui influence la cible — d'autres facteurs, non pris en compte ici, jouent probablement davantage |
| Point(s) atypique(s) détecté(s) | Une ou plusieurs lignes de données pèsent anormalement lourd dans le résultat — l'utilisateur est invité à les vérifier avant de se fier au résultat |
| Comparaisons multiples | Quand beaucoup de colonnes sont comparées entre elles, il est normal qu'une relation "ait l'air forte" par pur hasard — cet avertissement précise combien de relations restent fiables une fois ce risque pris en compte |
| Variation en % non fiable | La valeur de référence est trop proche de zéro pour qu'un pourcentage ait un sens (ex : passer de 0,1 à 0,3 "fait" +200%, ce qui est trompeur) — seules les valeurs réelles sont alors montrées |
| Corrélation ≠ causalité | Rappel systématique : une relation forte entre deux variables ne veut pas dire que l'une cause l'autre |
| Corrélations limitées à 50 colonnes | Si le fichier a plus de 50 colonnes numériques, seules les 50 premières sont comparées entre elles pour des raisons de rapidité — les statistiques de base (moyenne, etc.) restent, elles, calculées sur toutes les colonnes |

## 8. Fiabilité et confidentialité

- Le fichier déposé est traité pour produire le rapport, puis n'est pas conservé (pas de stockage persistant en Phase 1a/2)
- Aucune donnée personnelle ni compte utilisateur n'est demandé à ce stade
- Le résultat d'une même analyse, relancée sur le même fichier avec les mêmes paramètres, est identique à chaque fois (contrairement à un résultat obtenu via un assistant conversationnel généraliste, qui peut varier d'une fois à l'autre)

## 9. Pourquoi utiliser cet outil plutôt qu'un chat IA généraliste

Pour une question ponctuelle sur un petit jeu de données, un assistant conversationnel généraliste peut suffire. Ce produit apporte une valeur différente, utile en particulier :
- quand l'utilisateur veut un résultat garanti reproductible (même fichier, même résultat, à chaque fois)
- quand le fichier est trop volumineux pour être simplement collé dans une conversation
- quand l'utilisateur doit justifier une décision auprès d'un tiers (associé, banque, client) avec une méthode claire plutôt qu'une conversation
- quand l'utilisateur n'a pas le temps ou l'envie d'apprendre à bien formuler ses demandes à un assistant généraliste

## 10. Glossaire (langage utilisateur, pas technique)

- **Ligne / observation** : une entrée de votre fichier (ex : une vente, un animal, un mois)
- **Colonne / variable** : une caractéristique mesurée (ex : le prix, l'âge, le revenu)
- **Corrélation** : à quel point deux variables évoluent ensemble (proche de -1 ou +1 = lien fort ; proche de 0 = pas de lien apparent)
- **R²** : un score entre 0 et 1 qui indique la part de la variation de votre cible expliquée par la variable choisie (proche de 1 = explication forte ; proche de 0 = faible)
- **Simulation** : l'estimation de ce qui se passerait sur votre cible si vous changiez une variable d'un certain pourcentage
