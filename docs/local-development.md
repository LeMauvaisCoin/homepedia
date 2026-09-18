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
bun run dev              # API et frontend via Portless, avec rechargement
```

**Premier résultat attendu** : l’URL `homepedia` imprimée par Portless affiche un tableau de
douze communes, d'Annecy à Valence, avec « 12 territoires — page 1 sur 3 ».
La recherche « lyon » ne garde que Lyon (69123) et s'inscrit dans l'URL
(`?q=lyon`). Côté API, le chemin `/api/v1/territories?limit=2` sur cette même URL renvoie
Annecy puis Aurillac avec `"total": 12`, et le chemin `/docs` sur l’URL locale `api.homepedia`
présente le contrat OpenAPI.

## Portless et accès depuis le Mac

Portless **0.15.6** attribue un port libre à chaque application. Le proxy local
HTTPS utilise le port non privilégié `1355`. Les noms sont
`homepedia.localhost` et `api.homepedia.localhost` ; dans un worktree lié,
Portless ajoute le nom de branche normalisé devant chacun. Utiliser les URL
imprimées, ou `bun run dev:urls`, plutôt que des ports d’application fixes.

Au premier démarrage sur une nouvelle machine, lancer une fois dans un terminal
interactif `bunx --no-install portless proxy start --port 1355 --https` pour
créer et approuver l’autorité de certification locale. Cette étape peut
demander sudo. L’accès Tailscale utilise son propre certificat HTTPS, déjà
reconnu par le navigateur du Mac.

Pour accéder au frontend depuis une autre machine connectée au même tailnet :

```sh
bun run dev:tailnet
# Équivalent :
PORTLESS_TAILSCALE=1 bun run dev
```

Ouvrir l’URL « Tailscale » affichée pour `homepedia`. Portless choisit un port
HTTPS disponible sur `dev-tower` et conserve les autres partages. Le port peut
changer au prochain lancement. Tailscale doit être installé, connecté et
configuré pour HTTPS sur le serveur ; le Mac doit être connecté au même tailnet.

Le navigateur appelle `/api` sur cette même origine. Vite retire ce préfixe et
transmet la requête à l’URL fournie par `portless get api.homepedia`, dans le
même worktree. `changeOrigin` permet au proxy Portless de choisir l’API et
`NODE_EXTRA_CA_CERTS`, fourni par Portless, valide son certificat local. L’API
n’a pas de partage Tailscale séparé. Aucun ajout CORS n’est nécessaire.

En mode Portless, `/api` remplace la valeur `VITE_API_URL` du fichier `.env`
pour éviter que le Mac appelle son propre localhost. `DEV_API_URL` permet de
remplacer la cible interne du proxy, via l’environnement ou `apps/web/.env.local`.
Le build, le preview et les tests E2E conservent leur `VITE_API_URL` explicite.
Pour lancer directement les serveurs sans Portless, utiliser `bun run dev:app`
dans chaque application : le frontend revient à `5173`, l’API à `8000`.

`bun run dev:doctor` vérifie le proxy et `bun run dev:urls` affiche les routes.
Arrêter le processus `dev` avec Ctrl-C supprime ses routes et son partage
Tailscale. Le proxy commun reste disponible pour les autres projets. Ne pas
lancer `tailscale serve reset`, `portless clean` ou `portless proxy stop` pour
arrêter seulement Homepedia.

Le patch `patches/portless@0.15.6.patch`, repris de Wondday, sérialise les
inscriptions et suppressions Tailscale entre projets et worktrees via
`~/.portless/tailscale.lock`. Il retente les conflits transitoires de configuration.
`bun install` l’applique automatiquement. En cas d’expiration du verrou, vérifier
le processus propriétaire avant d’intervenir ; un verrou vide après un arrêt
brutal ne doit être retiré qu’une fois les processus Portless concernés arrêtés.

## Applications

| Chemin                | Application                               | Démarrage seul           | Adresse locale                                          |
| --------------------- | ----------------------------------------- | ------------------------ | ------------------------------------------------------- |
| `apps/web`            | Frontend React/Vite (SPA)                 | `bun run dev:web`        | URL Portless `homepedia`                                |
| `apps/api`            | API FastAPI                               | `bun run dev:api`        | URL Portless `api.homepedia`                            |
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
| `bun run generate`         | Tables SQLAlchemy (base locale), contrat OpenAPI, client TypeScript |
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
| `apps/web/.env` | `VITE_API_URL`, `DEV_API_URL` (proxy local optionnel) | T3 Env + Zod, au `vite dev`/`vite build` et au chargement de la page |
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
