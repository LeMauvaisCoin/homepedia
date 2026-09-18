# Vendored padding-line-between-statements

Source: [ESLint Stylistic](https://github.com/eslint-stylistic/eslint-stylistic), commit `435c3ea0fd26a5fef9042c4b36b6e165fbbf8d08`.

Copied files:

- `packages/eslint-plugin/rules/padding-line-between-statements/padding-line-between-statements.ts`
- `packages/eslint-plugin/rules/padding-line-between-statements/types.d.ts` → `padding-line-options.d.ts`
- Root `LICENSE`, retained verbatim. Both OpenJS Foundation and ESLint Stylistic notices apply.

The rule is MIT-licensed. Keep `LICENSE` with every redistributed copy, including skill assets. No Stylistic, ESLint, TypeScript-ESLint, or additional parser runtime dependency is required.

## Local adaptations

- Replace upstream type aliases with Oxlint's ESTree, context, token/comment, and rule types. Upstream's token type includes comments; Oxlint exposes those separately.
- Replace `AST_NODE_TYPES` enum members with identical string literals.
- Guard indexed reads for consuming repositories with `noUncheckedIndexedAccess`. Impossible missing AST/configuration entries raise explicit invariant errors rather than introducing new non-null assertions.
- Replace the repository-specific `createRule` factory with `createPaddingLineRule(options)`. The anti-slop wrapper supplies typed options directly; it exposes no user configuration options.
- Implement the small required AST helper surface in `padding-line-ast.ts` using Oxlint's public source-code/token API.
- Retain the statement matchers used by the fixed policy, scope tracking, comment-aware insertion, selector support, and diagnostic text. Unused matchers, selector line modes, blank-line removal, and the public options schema are omitted; the wrapper accepts no user options. Upstream naming and non-null assumptions remain localized here to keep future diffs reviewable; the file is not a model for new application code.

The opinionated policy lives outside this directory in `../../rules/require-readable-spacing.ts`. It adds spacing without collapsing existing blank lines. Short local bindings, consecutive imports, and adjacent overload signatures/implementation remain grouped. Spacing is syntactic, not an inference of business-logic boundaries.

## Updating and verification

Fetch an explicit upstream revision, compare the original rule and types against this revision, and port relevant fixes while retaining the adapters and fixed-policy subset above. Update this record and preserve the license. Run `bun run lint`, `bun run build`, and `bun run test`.

The fixed-policy reduction was checked against the original vendored plugin on 800 valid TypeScript/TSX files: 626 generated fixtures (statement pairs, comments, semicolon-free code, exports, overloads, and nested scopes) plus 174 application source files with blank lines removed. All 5,002 diagnostics and all autofixed files matched. The complete upstream JS/TS test suites have not been ported; this is focused compatibility evidence, not a claim of full upstream conformance.
