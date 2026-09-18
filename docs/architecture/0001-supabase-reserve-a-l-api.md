# ADR-0001 — Supabase n'est accessible que par l'API

Statut : accepté (18 septembre 2026, [LEM-9](https://linear.app/lemauvaiscoin/issue/LEM-9)).

## Contexte

Le frontend est une SPA. Supabase permettrait au navigateur d'interroger
PostgreSQL directement (PostgREST, supabase-js) sous contrôle de la RLS.
L'architecture retenue place pourtant les services métier Python entre la
base et tous les clients : interface, API publique et MCP.

## Décision

Aucun client ne parle à PostgreSQL : seuls les services Python le font.
L'API FastAPI aujourd'hui, puis le MCP à travers les mêmes fonctions de
requête, et les pipelines pour publier. La Data API, Auth, Realtime, Storage
et les Edge Functions sont désactivés dans `supabase/config.toml`. Chaque
table active la RLS sans policy : si la Data API était rouverte par erreur,
les rôles `anon` et `authenticated` ne verraient rien. L'API se connecte avec
un rôle serveur qui contourne la RLS, et écrit ses requêtes avec SQLAlchemy
Core ([ADR-0002](0002-requetes-sqlalchemy-core.md)).

## Raisons

- Les requêtes du produit (agrégations, comparaisons, filtres spatiaux,
  pagination avec effectifs et provenance) ne s'expriment pas dans PostgREST
  sans fonctions SQL, ce qui dupliquerait la logique partagée avec le MCP.
- L'identité vient de Clerk et FastAPI vérifie les jetons : un accès direct
  imposerait l'intégration Clerk ↔ Supabase, des policies par table et leurs
  tests pgTAP, soit un second système d'autorisation.
- Un seul contrat typé : Pydantic → OpenAPI → `packages/api-client`. Pas de
  types Supabase générés ni de supabase-js dans le frontend.
- L'expérience n'y perd pas : le saut réseau supplémentaire reste dans la
  même région, et la fluidité vient du cache et du préchargement de TanStack
  Query.

## Conséquences

- Pas de tests RLS tant que cette décision tient.
- Le temps réel (suivi des ingestions, flux contextuel) passera par l'API
  (SSE ou WebSocket). Rouvrir Realtime pour ce seul besoin resterait possible
  et demanderait de réviser cet ADR.
