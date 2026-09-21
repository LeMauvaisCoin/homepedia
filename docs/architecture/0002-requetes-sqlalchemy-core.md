# ADR-0002 — Les requêtes de l'API s'écrivent avec SQLAlchemy Core

Statut : accepté (18 septembre 2026, [LEM-9](https://linear.app/lemauvaiscoin/issue/LEM-9)).

## Contexte

La première route écrivait son SQL en chaînes, avec psycopg. Le filtre y
figurait deux fois : une pour la page, une pour le total. Le backlog demande
davantage à la même sélection :

- filtres, tri et pagination côté serveur sur tout le résultat filtré
  ([LEM-25](https://linear.app/lemauvaiscoin/issue/LEM-25),
  [LEM-24](https://linear.app/lemauvaiscoin/issue/LEM-24)) ;
- la page, son total, l'agrégat de la carte, l'export CSV complet
  ([LEM-31](https://linear.app/lemauvaiscoin/issue/LEM-31)) et l'outil MCP
  ([LEM-35](https://linear.app/lemauvaiscoin/issue/LEM-35)), avec les mêmes
  valeurs ;
- des jointures indicateur × territoire × période × publication, du PostGIS,
  du JSONB et de la recherche plein texte.

## Décision

Les requêtes s'écrivent avec SQLAlchemy 2 Core, en asynchrone sur psycopg 3,
avec GeoAlchemy2 pour les types spatiaux. L'ORM n'est pas utilisé.

- `homepedia_api/tables.py` est généré par sqlacodegen depuis la base locale
  migrée (`bun run generate`) : tables et vues du schéma `public`.
  `supabase/migrations` reste la source de vérité et le fichier ne se modifie
  jamais à la main.
- `homepedia_api/repositories/` porte les requêtes. Une fonction construit la
  sélection filtrée, sans tri ni pagination ; la page, le total, les agrégats
  et les exports en dérivent. Les routes ne contiennent pas de SQL, et le MCP
  appellera ces mêmes fonctions.
- Un tri dynamique passe par un dictionnaire de colonnes autorisées, jamais
  par un nom de colonne reçu du client.
- Ce qui vaut pour toutes les requêtes (publication courante, géométries
  simplifiées, tuiles) s'écrit en vues ou fonctions SQL dans les migrations,
  puis se déclare dans `tables.py`.
- Les fonctions PostGIS sont qualifiées par `extensions.` (`db.postgis`).
- Les requêtes préparées sont désactivées (`prepare_threshold=None`) : Supabase
  ne les garantit pas derrière son pooler en mode transaction. L'API, serveur
  persistant, vise plutôt la connexion directe ou le mode session ; ce réglage
  évite qu'un changement de `DATABASE_URL` ne casse la production.

## Raisons

- Composer une sélection puis en dériver plusieurs lectures ne se fait pas
  proprement avec des chaînes : le filtre se duplique et le tri dynamique
  devient une surface d'injection.
- Core couvre le SQL attendu (CTE, fenêtres, `LATERAL`, JSONB, `tsvector`,
  PostGIS) et laisse `text()` pour le reste.
- L'API lit surtout des agrégats publiés par les pipelines : un ORM n'apporte
  ni identité d'objet ni unité de travail utiles ici. Les rares écritures
  ([LEM-28](https://linear.app/lemauvaiscoin/issue/LEM-28)) restent simples
  en Core.
- Générer `tables.py` plutôt que l'écrire évite une seconde description du
  schéma à maintenir. `bun run generate` a donc besoin de la base locale ;
  seul l'export OpenAPI reste exécutable hors ligne.

## Conséquences

- Une migration se committe avec le `tables.py` régénéré. La CI reconstruit
  la base, relance la génération (`bun run generate:check`) et refuse toute
  différence.
- `tables.py` est exclu de Ruff, comme le client TypeScript généré l'est
  d'Oxlint et d'Oxfmt.
- Les limites de durée (`statement_timeout`) et les index se décident sur
  mesures ([LEM-38](https://linear.app/lemauvaiscoin/issue/LEM-38)).
- Si les exports dépassent ce que PostgreSQL sert confortablement, lire les
  Parquet de R2 resterait possible et demanderait de réviser cet ADR.
