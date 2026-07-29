# Decision Intelligence Engine

Un moteur de décision, pas une application — l'interface web n'est qu'une façade sur un moteur de calcul statistique fiable et déterministe.

## Documentation

| Document | Contenu |
|---|---|
| [`FUNCTIONAL_SPEC.md`](./FUNCTIONAL_SPEC.md) | Ce que fait le produit, en langage utilisateur — parcours, formats acceptés, avertissements expliqués, glossaire |
| [`SPEC.md`](./SPEC.md) | Spécification technique complète — vision, roadmap, architecture, modules, API, tests, conventions |

Ce README reste volontairement court : il évite de dupliquer des détails (compteurs de tests, décisions d'architecture, statuts de phase) qui vivent dans `SPEC.md` et se désynchronisent sinon à chaque changement.

## Démarrage rapide

```bash
# Moteur
cd decision-core && pip install -e . && pytest tests/

# API
cd decision-engine && pip install -e ../decision-core -r requirements.txt
uvicorn main:app --reload

# Interface
cd frontend && npm install && npm run dev
```

## Structure du repo

```
decision-intelligence/
├── decision-core/     # moteur Python, testé indépendamment
├── decision-engine/   # façade FastAPI
├── frontend/          # interface React
├── FUNCTIONAL_SPEC.md
└── SPEC.md
```
