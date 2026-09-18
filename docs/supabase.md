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
bun run test:integration
```

Règles :

- une migration fusionnée ne se modifie plus : corriger par une nouvelle ;
- toute nouvelle table active la RLS sans policy (ADR-0001) ;
- les codes géographiques sont des `text`, jamais des entiers ;
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
bunx supabase link --project-ref <ref-du-projet> --workdir .
```

Puis, depuis `main` à jour :

```sh
bun run supabase:deploy:plan   # liste les migrations en attente, sans rien appliquer
bun run supabase:deploy        # applique les migrations, puis pousse config.toml
```

La CLI affiche ce qu'elle va appliquer et demande confirmation à chaque étape.
Le seed n'est pas poussé (`--include-seed` n'est jamais utilisé). L'état du
lien (`supabase/.temp/`) reste local et ignoré par Git.

Le projet hébergé n'existe pas encore : il sera créé avec
[LEM-34](https://linear.app/lemauvaiscoin/issue/LEM-34).
