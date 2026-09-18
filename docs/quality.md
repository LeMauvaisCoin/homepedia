# Qualité du code, hooks et CI

## Outils

| Domaine            | Outil                                                                | Configuration                     |
| ------------------ | -------------------------------------------------------------------- | --------------------------------- |
| Lint TypeScript    | Oxlint + `oxlint-tsgolint` (règles typées et erreurs de compilation) | `.oxlintrc.json`                  |
| Anti-slop          | Plugin vendorisé `tools/oxlint/anti-slop`                            | `.oxlintrc.json`                  |
| Interface          | `@shadcn/lint`, sur `apps/web/src`                                   | `.oxlintrc.json`                  |
| Formatage          | Oxfmt (TS, JSON, Markdown, YAML, CSS, TOML) ; Ruff pour Python       | `.oxfmtrc.json`, `pyproject.toml` |
| Typecheck          | `tsc` de TypeScript 7 ; `ty` pour Python                             | `tsconfig.base.json`              |
| Lint Python        | Ruff                                                                 | `pyproject.toml`                  |
| Code mort          | Knip                                                                 | `knip.jsonc`                      |
| Messages de commit | commitlint, Conventional Commits                                     | `commitlint.config.mjs`           |

Versions épinglées ensemble : `oxlint` et `@oxlint/plugins` à la même version,
`oxlint-tsgolint` et `typescript` 7. Les mettre à jour dans la même PR.

Le code généré n'est ni linté ni formaté : `packages/api-client/src/generated`
pour Oxlint et Oxfmt, `apps/api/src/homepedia_api/tables.py` pour Ruff
(sqlacodegen écrit les contraintes SQL sur une ligne, au-delà de la largeur
autorisée). `bun run generate:check` garantit qu'ils ne sont pas modifiés à la
main.

`bun run lint:root` lance Oxlint une fois sur tout le dépôt ; le lint typé
porte donc toujours sur le projet complet. Lint, typecheck (`tsc --noEmit`) et
build (`vite build`) sont trois contrôles distincts : chacun détecte ses
propres erreurs.

### Anti-slop

Copie de [dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop) à une
révision identifiée, licence MIT conservée : voir
`tools/oxlint/anti-slop/UPSTREAM.md`. Le dossier est exclu du lint, du
formatage et de Knip. Les règles refusent notamment `unknown` en paramètre ou
en retour, les assertions de type sans commentaire `SAFETY:`, le mocking de
modules et les copies d'accumulateur dans `reduce`. Valider les entrées à la
frontière (Zod) plutôt que contourner une règle.

### shadcn

Les six règles `shadcn/*` sont en erreur dans `apps/web/src`. L'apparence
appartient aux composants : `className` sert au placement, un nouveau
traitement visuel devient une variante du composant (exemple : `numeric` sur
`TableCell`). Dans `components/ui`, `no-restyle`, `require-static-classes` et
`no-arbitrary-values` sont désactivées : les primitives générées par la CLI
shadcn possèdent leur apparence et restent régénérables sans retouche.

## Hooks Git

Installés par `bun install` (Husky). Ne jamais les contourner
(`--no-verify`, `HUSKY=0`).

| Hook         | Contrôle                                                             |
| ------------ | -------------------------------------------------------------------- |
| `pre-commit` | lint-staged sur les fichiers indexés : Oxfmt, Oxlint `--fix`, Ruff   |
| `commit-msg` | Conventional Commits                                                 |
| `pre-push`   | Refuse un push direct vers `main` ou `staging`, puis `bun run check` |

lint-staged met de côté les modifications non indexées : un fichier
partiellement indexé garde sa partie hors index intacte. Les hooks ne lancent
ni ingestion, ni appel réseau payant, ni test dépendant de la base.

## CI

`.github/workflows/ci.yml`, sur chaque PR et sur `main`/`staging`, avec les
runners hébergés par GitHub :

| Job     | Contenu                                                                                                                                                                                          |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `knip`  | Code, exports et dépendances inutilisés                                                                                                                                                          |
| `check` | Conventional Commits de la PR, formatage, lint typé, typecheck, tests unitaires, build                                                                                                           |
| `e2e`   | Base locale Supabase (migrations + seed), lint SQL, tables, contrat et client régénérés sans différence, tests d'intégration de l'API, scénarios Playwright ; rapport en artefact en cas d'échec |

Les trois jobs sont à rendre obligatoires dans la protection de `main` et
`staging`. La CI ne déploie rien et n'applique aucune migration distante.
