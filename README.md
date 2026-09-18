# Homepedia

Projet d’exploration des données immobilières — Léo Mathurin, Mathias Arnaud et Bastien Cochet.

Rendu : **7 février 2027 à 23:42 (Europe/Paris)**.

## Documentation et suivi

Le [projet Linear Homepedia](https://linear.app/lemauvaiscoin/project/homepedia-a97119179671) centralise tickets, décisions et documents. Le PDF original du sujet est dans ses ressources.

- [Cahier des charges et organisation](https://linear.app/lemauvaiscoin/document/cahier-des-charges-et-organisation-1b508f19b9ad)
- [Architecture et contrats API-MCP](https://linear.app/lemauvaiscoin/document/architecture-et-contrats-api-mcp-54b0c0b89a29)
- [Catalogue des sources et qualité des données](https://linear.app/lemauvaiscoin/document/catalogue-des-sources-et-qualite-des-donnees-60ac4ecc2f85)
- [Qualité du code et livraison](https://linear.app/lemauvaiscoin/document/qualite-du-code-et-livraison-b43ff19cfa44)
- [Infrastructure, stockage et budget](https://linear.app/lemauvaiscoin/document/infrastructure-stockage-et-budget-f958bce1ce6e)
- [Documentation API-MCP avec Mintlify](https://linear.app/lemauvaiscoin/document/documentation-api-mcp-avec-mintlify-965e4cf3ee77)
- [Références UX et vocabulaire](https://linear.app/lemauvaiscoin/document/references-ux-et-vocabulaire-710b4cf5b498)

## Développement

Dépôt principal : [leo-mathurin/homepedia](https://github.com/leo-mathurin/homepedia) (`origin`). Le remote `epitech` est réservé à la remise finale.

Branches persistantes : `main` pour la production, `staging` pour l’intégration testée uniquement en local. Backlog partagé, tâches prises librement et petites PR ; aucun domaine réservé.

### Démarrage local

Prérequis : [Bun](https://bun.sh) 1.4.0, Node.js 24, [uv](https://docs.astral.sh/uv/) et Docker. Aucun compte cloud n’est nécessaire.

```sh
bun install              # dépendances JavaScript et hooks Git
bun run setup            # fichiers .env locaux et environnement Python
bun run supabase:start   # PostgreSQL/PostGIS local : migrations + jeu d’exemple
bun run dev              # URL HTTPS locales et ports libres avec Portless
bun run dev:tailnet      # accès depuis le Mac via Tailscale
```

Ouvrir l’URL affichée pour `homepedia` (`bun run dev:urls` pour la retrouver) : elle affiche les douze communes du jeu d’exemple. Pour le premier démarrage et les URL par worktree, voir le [guide local](docs/local-development.md).

| Chemin                | Contenu                                                  |
| --------------------- | -------------------------------------------------------- |
| `apps/web`            | Frontend React/Vite, TanStack Router et Query, shadcn/ui |
| `apps/api`            | API FastAPI/Pydantic, dépendances gérées par uv          |
| `packages/api-client` | Client TypeScript généré depuis le contrat OpenAPI       |
| `supabase`            | Configuration, migrations SQL et jeu d’exemple           |
| `tools/oxlint`        | Plugin Oxlint anti-slop vendorisé                        |

Avant de pousser : `bun run check`. Guides : [développement local](docs/local-development.md), [contrat de l’API](docs/api-contract.md), [Supabase et migrations](docs/supabase.md), [qualité, hooks et CI](docs/quality.md). Les consignes pour les agents sont dans [AGENTS.md](AGENTS.md).
