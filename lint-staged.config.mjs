// Formatting and safe fixes on staged files only; typed lint and tests cover
// the whole project and run on pre-push and in CI.
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
