# Homepedia monorepo

Bun workspaces + Turborepo for JavaScript, uv workspace for Python.
`apps/web` (React/Vite SPA), `apps/api` (FastAPI), `packages/api-client`
(generated), `supabase/` (PostgreSQL/PostGIS). Product scope, decisions and
backlog live in the [Linear project](https://linear.app/lemauvaiscoin/project/homepedia-a97119179671).

Before changing:

- how the repo starts locally, ports, env files or the example dataset, read
  [docs/local-development.md](docs/local-development.md);
- API routes or models, read [docs/api-contract.md](docs/api-contract.md) and
  run `bun run generate` in the same commit. Never hand-edit
  `apps/api/openapi.json` or `packages/api-client/src/generated`;
- the database, read
  [ADR-0001](docs/architecture/0001-supabase-reserve-a-l-api.md) and
  [docs/supabase.md](docs/supabase.md). The frontend never talks to Supabase;
- lint rules, hooks or CI, read [docs/quality.md](docs/quality.md).

## Commands

- `bun run check`: typed lint, typecheck, unit tests. Run it before saying a
  change is done.
- `bun run format`, `bun run knip`, `bun run generate:check`.
- `bun run test:integration` and `bun run test:e2e` need the local database:
  `bun run supabase:start`.

## Conventions

- Use Bun for JavaScript and uv for Python. Never npm, pnpm, pip or poetry.
- Conventional Commits in English. Link Linear in the commit body with
  `refs LEM-123`, or `fixes LEM-123` only when the commit should close the
  issue after merge. Use the issue's suggested branch name.
- Use the Composio connection `lemauvaiscoin`. The Linear team is `LEM`.
- Documentation and user-facing text are in French; code, identifiers and
  commit messages are in English.
- Open pull requests against `staging`. Never push to `staging` or `main`
  directly; promotion `staging` → `main` is a merge, never a squash.
- Never skip Git hooks (`--no-verify`, `HUSKY=0`) and never silence a lint
  rule to get a change through: fix the code, or change the rule in its own
  commit with the reason in [docs/quality.md](docs/quality.md).
- Geographic codes are strings everywhere (`"01053"`), never numbers.
- Do not add a package, app or dependency without a real consumer in the
  same pull request; Knip fails the build otherwise.

## Authority limits

- Without explicit human instruction, do not deploy, run
  `bun run supabase:deploy`, create or rotate secrets, subscribe to a paid
  service, or touch the `epitech` remote. Remote reads are allowed.
- Secrets never enter Git, `.env.example` files or `VITE_` variables.
- Record a decision that spans several pull requests as an ADR in
  `docs/architecture/`, in the same pull request as the change it explains.
