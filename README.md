# Decision Intelligence Engine

## Vision

L'objectif n'est pas de créer une application, mais un **moteur de décision** (Decision Core). L'interface web n'est qu'une façade ; le véritable produit est le moteur de calcul statistique, fiable et déterministe, sur lequel des couches (interface, IA, SaaS) viennent s'appuyer progressivement.

Trois objectifs guident ce projet, avec des critères de succès différents :

| Objectif | Ce qui compte | Ce qui ne compte pas |
|---|---|---|
| Portfolio (recrutement) | Rigueur mathématique visible, code testé et documenté | Produit fini, UI soignée |
| Usage personnel / entourage | Aide réelle à la décision, rapidité | Robustesse, scalabilité |
| SaaS | Marché validé, simplicité pour un non-matheux | Sophistication excessive |

## Roadmap

- **Phase 0 — Foundation** (3-5 j) : architecture, standards, conventions.
- **Phase 1a — Decision Core Foundation** : import, validation, profiling, statistiques, simulation simple, rapport. *Jalon : Go/No-Go technique.* **✅ Complète, 63 tests.**
- **Phase 1a.5 — Validation légère** : le rapport est montré à 5-10 personnes cibles avant d'aller plus loin. *Jalon : désirabilité confirmée ou non.*
- **Phase 1b — Decision Core Analytics** : Monte Carlo, corrélations, incertitude, distributions, sensibilité. *Jalon : API stable v1.0.*
- **Phase 2 — Decision Studio** : interface React + façade FastAPI. **🚧 decision-engine initialisé, 11 tests.**
- **Phase 3 — Decision Intelligence** : prédiction, risque, recommandation.
- **Phase 4 — AI Layer** : explications en langage naturel, chat, RAG.
- **Phase 4.5 — Market Validation** : tests utilisateurs approfondis, cas d'usage, feedback.
- **Phase 5 — Decision Cloud** : NestJS (auth, organisations, facturation, API), Supabase (BDD + Storage).
- **Phase 6 — Decision Ecosystem** : marketplace, connecteurs, SDK, API publique.

## Architecture (voir ARCHITECTURE.md pour le détail)

```
React → FastAPI (decision-engine) → decision-core        [maintenant]
React → NestJS → FastAPI (decision-engine) → decision-core [Phase 5]
```

`decision-core` reste toujours agnostique de tout ce qui est utilisateur/organisation — seul ce qui l'entoure change selon la phase.

## Limites de la Phase 1a

Volontaires, pas des oublis — chacune correspond à une fonctionnalité repoussée sciemment à une phase ultérieure.

- **Formats acceptés** : CSV et Excel uniquement. Une seule feuille par fichier Excel.
- **Une seule table à la fois** : pas de jointure entre plusieurs fichiers.
- **Volume** : fiable jusqu'à quelques centaines de milliers de lignes avec pandas.
- **Détection de type heuristique** : peut se tromper (ex. un prix en valeurs entières classé "discret" plutôt que "continu" — cas réel rencontré et documenté par un test, cf. `test_type_detection.py`).
- **Pas de nettoyage automatique** : valeurs manquantes, doublons et anomalies sont signalés, jamais corrigés automatiquement.
- **Détection d'anomalies peu fiable sous ~30 lignes** — signalé explicitement dans le rapport.
- **Simulation via régression linéaire uniquement** (simple ou multivariée) : pas de sélection automatique de modèle — Phase 3.
- **Aucune règle métier intégrée.**
- **Corrélation ≠ causalité** : rappelé explicitement dans chaque rapport.
- **Priorité aux relations non triviales** : le moteur évite de présenter comme "insight principal" une corrélation dont le sens est déjà évident avant analyse.

## Choix du modèle statistique (Phase 1a)

Automatique et fixe : régression linéaire simple ou multiple. Assumé pour l'interprétabilité totale, la fiabilité sur petits échantillons, et la cohérence avec le niveau de sophistication visé à ce stade. D'autres familles (Random Forest, XGBoost, GAM, bayésien...) sont repoussées à la Phase 3.

## Pourquoi pas simplement coller les données dans un chat IA générique ?

Pour une analyse ponctuelle sur un petit jeu de données, un chat IA générique suffit très bien — pas la peine de se raconter le contraire, notamment pour un usage personnel occasionnel.

Un moteur dédié apporte une valeur différente :
- **Fiabilité des calculs** : un LLM génère du texte statistiquement plausible, pas un calcul garanti ; un moteur qui exécute du code (numpy/scipy) est déterministe et reproductible.
- **Volume de données** : pas de limite de fenêtre de contexte.
- **Reproductibilité et auditabilité** : méthode documentée, versionnée, rejouable à l'identique.
- **Automatisation** : API appelable sans intervention humaine, intégrable à un pipeline.
- **Coût à l'échelle** : moins cher qu'un appel LLM répété pour chaque analyse.

**Et si l'utilisateur maîtrise déjà très bien le prompting ?** L'écart se réduit, il faut le reconnaître honnêtement. Ce qui reste vrai : le déterminisme est un problème structurel du LLM (pas de compétence de prompting) ; l'automatisation/intégration système reste hors de portée d'un chat ; la légitimité externe d'un rapport documenté pèse plus qu'une conversation, même bien menée, face à un tiers (investisseur, régulateur, associé). Ce moteur cible les utilisateurs qui n'ont ni le temps ni l'envie de développer cette compétence, ou qui ont besoin de résultats reproductibles pour des raisons professionnelles — pas l'utilisateur déjà expert en prompting.

## Développement (TDD)

```bash
cd decision-core && pip install -e . && pytest tests/
cd decision-engine && pip install -e ../decision-core -r requirements.txt && pytest tests/
```

63 tests `decision-core` + 11 tests `decision-engine`. Fixtures = 3 datasets réels (retail, élevage, finance) utilisés dans les exemples de ce README.
