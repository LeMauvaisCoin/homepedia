# Anti-slop upstream

Source: https://github.com/dmmulroy/anti-slop

Revision: `c44ef22ca116d0ba62a3ff663a0bd13a3f3fa40b`

Copied `src/` excluding upstream tests and the unused opt-in `effect/` rules. The unused `no-array-filter-map`, `no-conditional-empty-object-spread`, and `no-runtime-typeof` rules are omitted. The vendored spacing implementation is restricted to this project’s fixed policy; see its nested provenance record. MIT license included; nested vendor licenses and provenance preserved.

Further local reductions remove the unreferenced `isPopulatedObjectExpression` helper and fix assertion-comment markers to the configured `SAFETY:` policy, dropping unused marker options, pattern generation, and caching. Array-method analysis reuses the existing lexical scope resolver. The spacing rule tracks whether padding exists without storing token pairs or dispatching a no-op policy. These changes are checked by comparing diagnostics and autofixed output against the previous implementation.

Homepedia copies this directory unchanged from `blocker-app/blocker-app` at `e62767be6d32ca222cd573476d993d4d48c6fa70`, where the reductions above were made.
