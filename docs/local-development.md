# Développement local

Depuis une copie neuve, ces étapes lancent le frontend, l'API et le jeu
d'exemple, sans aucun compte cloud. Elles servent de base au quickstart
Mintlify ([LEM-40](https://linear.app/lemauvaiscoin/issue/LEM-40)).

## Prérequis

| Outil                                        | Version          | Rôle                                                       |
| -------------------------------------------- | ---------------- | ---------------------------------------------------------- |
| [Bun](https://bun.sh)                        | 1.4.0            | Dépendances JavaScript et scripts (`.bun-version`)         |
| [Node.js](https://nodejs.org)                | 24               | Exécution de Vite, Playwright et du générateur             |
| [uv](https://docs.astral.sh/uv/)             | 0.12 ou plus     | Python 3.13 et dépendances Python (`uv.lock`)              |
| [Docker](https://docs.docker.com/get-docker) | moteur en marche | Base PostgreSQL/PostGIS locale pilotée par la CLI Supabase |

La CLI Supabase, Turborepo, Oxlint et Playwright sont installés par
`bun install` : rien d'autre à installer globalement.

## Démarrage

```sh
bun install              # dépendances JavaScript et hooks Git
bun run setup            # apps/*/.env depuis .env.example, puis uv sync
bun run supabase:start   # PostgreSQL local : migrations + jeu d'exemple
bun run dev              # API et frontend, avec rechargement
```

**Premier résultat attendu** : <http://localhost:5173> affiche un tableau de
douze communes, d'Annecy à Valence, avec « 12 territoires — page 1 sur 3 ».
La recherche « lyon » ne garde que Lyon (69123) et s'inscrit dans l'URL
(`?q=lyon`). Côté API, <http://localhost:8000/v1/territories?limit=2> renvoie
Annecy puis Aurillac avec `"total": 12`, et <http://localhost:8000/docs>
présente le contrat OpenAPI.

## Applications

| Chemin                | Application                               | Démarrage seul           | Adresse locale                                          |
| --------------------- | ----------------------------------------- | ------------------------ | ------------------------------------------------------- |
| `apps/web`            | Frontend React/Vite (SPA)                 | `bun run dev:web`        | <http://localhost:5173>                                 |
| `apps/api`            | API FastAPI                               | `bun run dev:api`        | <http://localhost:8000>                                 |
| `supabase`            | PostgreSQL 17 + PostGIS, Studio           | `bun run supabase:start` | base `127.0.0.1:55322`, Studio <http://127.0.0.1:55323> |
| `packages/api-client` | Client TypeScript généré (pas de serveur) | `bun run generate`       | —                                                       |

`apps/mcp`, `apps/docs` et `pipelines` arriveront avec leurs tickets : le
dépôt ne contient pas de package sans consommateur.

Chaque application porte ses propres scripts (`package.json`) ; Turborepo les
orchestre depuis la racine. `dev` est persistant et jamais mis en cache, tout
comme les tâches qui touchent la base (`test:integration`, `test:e2e`).

## Commandes

| Commande                   | Effet                                                               |
| -------------------------- | ------------------------------------------------------------------- |
| `bun run check`            | Lint typé, typecheck et tests unitaires (aussi lancé au `git push`) |
| `bun run format`           | Oxfmt et Ruff sur tout le dépôt                                     |
| `bun run knip`             | Code, exports et dépendances inutilisés                             |
| `bun run test:integration` | Tests de l'API contre la base locale                                |
| `bun run test:e2e`         | Scénarios Playwright : build du frontend, API et base locale        |
| `bun run generate`         | Contrat OpenAPI puis client TypeScript                              |
| `bun run supabase:reset`   | Reconstruit la base depuis les migrations et le seed                |
| `bun run supabase:stop`    | Arrête la pile locale                                               |

Première exécution des scénarios : `bunx playwright install chromium` depuis
`apps/web`. Ils utilisent leurs propres ports (API 8100, frontend 4173) et ne
perturbent pas `bun run dev`.

## Jeu d'exemple

`supabase/seeds/example_territories.sql` contient les douze préfectures de la
région Auvergne-Rhône-Alpes : code INSEE, nom, département, région, population
municipale et centre. Origine : [API Découpage administratif](https://geo.api.gouv.fr/decoupage-administratif/communes)
(INSEE/IGN, Licence Ouverte 2.0), relevé du 18 septembre 2026. Bourg-en-Bresse
(`01053`) vérifie que les codes restent des chaînes avec leur zéro initial.

Le seed n'est chargé qu'en local (`supabase start`, `supabase db reset`) et en
CI. Il n'est jamais poussé vers la base hébergée.

## Services externes

Aucun n'est nécessaire pour explorer le jeu d'exemple. Les fonctions
suivantes en demanderont un lorsqu'elles seront livrées :

| Fonction                                     | Service                         | Ticket                                                  |
| -------------------------------------------- | ------------------------------- | ------------------------------------------------------- |
| Comptes, export, sauvegardes, administration | Clerk                           | [LEM-29](https://linear.app/lemauvaiscoin/issue/LEM-29) |
| Carte                                        | Mapbox (token public restreint) | [LEM-24](https://linear.app/lemauvaiscoin/issue/LEM-24) |
| Collecte et fichiers Parquet                 | Cloudflare R2                   | [LEM-20](https://linear.app/lemauvaiscoin/issue/LEM-20) |
| Traitements distribués                       | Databricks                      | [LEM-13](https://linear.app/lemauvaiscoin/issue/LEM-13) |
| Production                                   | Supabase, Railway, Vercel       | [LEM-34](https://linear.app/lemauvaiscoin/issue/LEM-34) |
| Documentation publiée                        | Mintlify                        | [LEM-33](https://linear.app/lemauvaiscoin/issue/LEM-33) |

## Configuration

| Fichier         | Variables                                             | Validation                                                           |
| --------------- | ----------------------------------------------------- | -------------------------------------------------------------------- |
| `apps/web/.env` | `VITE_API_URL`                                        | T3 Env + Zod, au `vite dev`/`vite build` et au chargement de la page |
| `apps/api/.env` | `ENVIRONMENT`, `DATABASE_URL`, `CORS_ALLOWED_ORIGINS` | Pydantic Settings, au démarrage de l'API                             |

Seules des valeurs publiques préfixées `VITE_` vont dans le frontend : elles
finissent dans le bundle. Les secrets restent côté serveur et ne sont jamais
versionnés ; les `.env.example` ne contiennent que les identifiants par défaut
de la pile locale. Une variable absente ou invalide arrête le build ou le
démarrage en nommant la variable, sans afficher sa valeur. L'export du contrat
OpenAPI ne lit aucune variable et fonctionne hors ligne.

## Dépannage

- **Port 5532x occupé** : une autre pile Supabase utilise les mêmes ports ;
  les ports de Homepedia sont fixés dans `supabase/config.toml`.
- **`connection refused` sur `/health/ready`** : la base n'est pas démarrée
  (`bun run supabase:start`). `/health` répond sans base.
