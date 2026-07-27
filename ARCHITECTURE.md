# Architecture

## Vue d'ensemble (état actuel — Phase 2)

```
React (à venir)  →  FastAPI (decision-engine)  →  decision-core
```

Pas de NestJS pour l'instant (prévu Phase 5). Pas d'auth, pas de
base de données, pas d'utilisateur — `decision-engine` reste une
façade fine et publique, cohérente avec le scope de la Phase 2.

## decision-engine

Rôle strict : recevoir un fichier via HTTP, appeler `decision-core`,
retourner le rapport en JSON. Aucune logique métier, aucune notion
d'utilisateur ou d'organisation ici — ce sera le rôle de NestJS à
partir de la Phase 5, sans que `decision-engine` ait besoin de changer.

### Endpoints

- `GET /health` — vérification de disponibilité
- `POST /engine/analyze` — reçoit un fichier (`file`, multipart) et,
  optionnellement, une configuration de simulation (`target`, `feature`,
  `change_pct`) ; retourne le rapport complet (`decision_core.report`)

### Limites appliquées

- Taille de fichier maximale : 50 Mo (`413` si dépassé)
- Formats acceptés : ceux supportés par `decision_core.importer`
  (CSV, Excel) ; `400` sinon

### Sécurité

Le middleware `verify_internal_key` vérifie le header `X-Internal-Key`
contre la variable d'environnement `INTERNAL_API_KEY` — **seulement si
cette variable est définie**. En Phase 2 (pas de NestJS), elle est
absente : le service reste ouvert au frontend. En Phase 5, NestJS
la définira des deux côtés (cf. discussion sécurité NestJS↔FastAPI) et
`decision-engine` deviendra interne, jamais exposé publiquement.

Plan de réponse en cas de fuite de clé : régénération immédiate
(`openssl rand -hex 32`), mise à jour synchrone des deux services,
redéploiement des deux en même temps pour éviter toute fenêtre de
validité de l'ancienne clé. La vraie protection reste l'isolation
réseau (service jamais exposé publiquement) ; la clé est une couche
de défense supplémentaire, pas la seule.

### Règle : exceptions métier de decision-core

Toute nouvelle exception typée levée par `decision-core` (ex.
`InsufficientDataError`, `UnsupportedFileFormatError`) doit être
ajoutée au tuple `DOMAIN_ERRORS` dans `decision-engine/main.py`.
Sans cet ajout, l'exception fuite en 500 brut avec stack trace
exposée au client plutôt qu'un 400 propre - un bug réel de ce type a
été trouvé et corrigé (cf. historique Git), d'où cette règle
explicite plutôt qu'implicite.

## Pourquoi le fichier ne transite jamais deux fois inutilement (Phase 2)

En Phase 2, le navigateur envoie le fichier directement à
`decision-engine` — un seul saut réseau. Le problème de double
transfert (navigateur → NestJS → FastAPI) identifié pour la Phase 5
sera résolu par upload direct vers Supabase Storage avec URL signée,
pas par un relai du fichier à travers NestJS.

## Développement local

```bash
cd decision-core && pip install -e . && pytest tests/
cd decision-engine && pip install -e ../decision-core -r requirements.txt
uvicorn main:app --reload
pytest tests/
```

## Tests

- `decision-core` : 63 tests (import, validation, types, profiling,
  anomalies, régression, simulation, rapport)
- `decision-engine` : 11 tests (endpoints, structure de réponse,
  limites de taille/format, middleware de sécurité)
