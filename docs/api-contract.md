# Contrat de l'API et client TypeScript

Les schémas de l'API n'existent qu'à un endroit : les modèles Pydantic et les
routes FastAPI de `apps/api`. Tout le reste en est dérivé.

```
apps/api (Pydantic, FastAPI)
  └─ bun run generate
       ├─ apps/api/openapi.json               contrat OpenAPI, versionné
       └─ packages/api-client/src/generated   types, SDK fetch, options TanStack Query
            └─ apps/web                        import { listTerritoriesOptions } from "@homepedia/api-client/react-query"
```

`openapi.json` servira aussi la référence Mintlify et le MCP.

## Modifier l'API

1. Changer les modèles ou les routes dans `apps/api`.
2. `bun run generate`, puis committer `openapi.json` et le client régénéré
   avec le changement.
3. La CI relance la génération (`bun run generate:check`) et refuse toute
   différence avec la copie versionnée. Le client ne se corrige jamais à la
   main ; il est exclu du lint et du formatage, mais compilé par le typecheck
   du frontend.

## Règles du contrat

- `operation_id` explicite et stable sur chaque route (`listTerritories`) : il
  nomme les fonctions du client et les pages de documentation.
- Descriptions et exemples dans le code Python (`Field(description=…,
examples=…)`), pas dans un fichier à part.
- Listes paginées : `limit`/`offset` bornés, réponse `{ items, total, limit,
offset }`.
- Erreurs au format `application/problem+json` (RFC 9457) via
  `homepedia_api.errors.Problem`, déclarées dans `responses` pour apparaître
  dans le contrat.
- L'export fonctionne hors ligne : `create_app()` ne lit ni configuration ni
  base de données.

## TypeScript 7 et le générateur

Le dépôt compile avec TypeScript 7, qui n'expose plus l'API JavaScript du
compilateur. `@hey-api/openapi-ts` en a besoin : `packages/api-client` épingle
donc `typescript@6.0.2` pour le seul générateur. Ne pas le remplacer par un
alias `npm:@typescript/typescript6` : Bun 1.4.0 échoue à résoudre le lockfile
avec cet alias.
