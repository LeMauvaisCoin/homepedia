# Supabase : configuration et migrations

`supabase/` est l'unique source de vérité de la base. Le frontend n'y accède
jamais : voir [ADR-0001](architecture/0001-supabase-reserve-a-l-api.md).

| Chemin                 | Rôle                                                                |
| ---------------------- | ------------------------------------------------------------------- |
| `supabase/config.toml` | Configuration locale et distante : services désactivés, ports       |
| `supabase/migrations/` | Migrations SQL versionnées, appliquées dans l'ordre des horodatages |
| `supabase/seeds/`      | Jeu d'exemple, local et CI uniquement                               |

## Écrire une migration

```sh
bunx supabase migration new <nom_en_snake_case> --workdir .
# éditer supabase/migrations/<horodatage>_<nom>.sql
bun run supabase:reset        # rejoue tout depuis zéro, seed compris
bun run supabase:lint         # plpgsql_check sur le schéma public
bun run generate              # régénère tables.py depuis la base migrée
bun run test:integration
```

Règles :

- une migration fusionnée ne se modifie plus : corriger par une nouvelle ;
- toute nouvelle table active la RLS sans policy (ADR-0001) ;
- les codes géographiques sont des `text`, jamais des entiers ;
- après `bun run supabase:reset`, lancer `bun run generate` et committer
  `apps/api/src/homepedia_api/tables.py` avec la migration
  ([ADR-0002](architecture/0002-requetes-sqlalchemy-core.md)) ;
- rester compatible avec la version précédente de l'API le temps d'un
  déploiement (ajouter, migrer, puis retirer dans une migration ultérieure) ;
- décrire le retour arrière dans la PR : migration inverse, ou restauration
  lorsque la migration détruit des données.

La CI reconstruit la base depuis les migrations et le seed à chaque PR, puis
lance le lint SQL, les tests d'intégration et les scénarios Playwright.

## Déployer depuis son poste

Les migrations sont suivies dans Git mais **ne sont jamais appliquées par la
CI** : le déploiement reste une décision humaine, depuis un poste local.

Une seule fois par poste :

```sh
bunx supabase login
bunx supabase link --project-ref wrahjubnsmbfmgnrepha --workdir .
```

Puis, depuis `main` à jour :

```sh
bun run supabase:deploy:plan   # liste les migrations en attente, sans rien appliquer
bun run supabase:deploy        # applique les migrations, puis pousse config.toml
```

La CLI affiche les changements et demande confirmation dans un terminal
interactif. En exécution non interactive, elle peut les accepter automatiquement :
examiner aussi `bunx supabase config diff` avant de pousser la configuration.
Le seed n'est pas poussé (`--include-seed` n'est jamais utilisé). L'état du
lien (`supabase/.temp/`) reste local et ignoré par Git.

## Projet hébergé

Le projet [homepedia](https://supabase.com/dashboard/project/wrahjubnsmbfmgnrepha)
est hébergé dans l'organisation **Homepedia**, en **Europe / Irlande
(`eu-west-1`)**, sur PostgreSQL 17 et l'offre gratuite. Sa référence publique
est `wrahjubnsmbfmgnrepha` ; ce n'est pas un identifiant secret.

La Data API est désactivée. La connexion applicative reste réservée à
FastAPI via `DATABASE_URL`, conservée dans l'environnement du serveur.
Le développement local garde sa base et son jeu d'exemple indépendants.

Quelle adresse mettre dans `DATABASE_URL` :

| Client                                             | Accès                                                                                                                       |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| API et MCP sur Railway                             | Connexion directe, `db.wrahjubnsmbfmgnrepha.supabase.co:5432`. Elle est en IPv6 : activer l'IPv6 sortant du service Railway |
| Poste de développement, GitHub Actions, Databricks | Pooler en mode session, `aws-1-eu-west-1.pooler.supabase.com:5432` (IPv4)                                                   |

L'API garde déjà son propre pool de connexions : un pooler externe ne lui
apporte rien. Le mode transaction (port `6543`) vise le serverless ; il perd
l'état de session (`SET`, `LISTEN/NOTIFY`, verrous consultatifs) et Supabase
n'y garantit pas les requêtes préparées. L'API fonctionne quand même à
travers lui, requêtes préparées désactivées
([ADR-0002](architecture/0002-requetes-sqlalchemy-core.md)).

La migration `20260918120000_example_territories.sql` a été appliquée lors
de l'initialisation du projet : PostGIS est installé, `public.territories`
active la RLS sans policy et la table reste vide. Aucun seed n'a été poussé.
Les options `enabled = false` des services dans `config.toml` pilotent la
pile locale ; elles ne garantissent pas l'arrêt de chaque service hébergé.
La désactivation de la Data API distante est vérifiée dans le dashboard
(Integrations → Data API → Settings). La CLI 2.117.0 signale encore
`api.enabled = true` dans `config diff` alors que ce réglage y est désactivé.
Aucune preview automatique par PR ni aucun déploiement GitHub n'est activé.

Le lien CLI reste dans `supabase/.temp/`, ignoré par Git. Le mot de passe de
la base ne doit pas être ajouté à la PR ou aux fichiers d'exemple.
Le déploiement de l'API et du frontend reste suivi dans
[LEM-34](https://linear.app/lemauvaiscoin/issue/LEM-34).
