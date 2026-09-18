// Formatage et corrections sûres sur les seuls fichiers indexés ; le lint typé
// et les tests portent sur le projet complet et tournent au pre-push et en CI.
export default {
  "*.{js,jsx,ts,tsx,mjs,cjs,json,jsonc,md,yml,yaml,css,html,toml}": [
    "oxfmt --write --no-error-on-unmatched-pattern",
  ],
  "*.{js,jsx,ts,tsx,mjs,cjs}": [
    "oxlint --fix --deny-warnings --no-error-on-unmatched-pattern",
  ],
  "*.py": [
    "uv run --package homepedia-api ruff check --fix",
    "uv run --package homepedia-api ruff format",
  ],
};
