// Prepares a fresh clone: local .env files and the Python environment.
import { copyFile } from "node:fs/promises";
import { $ } from "bun";

const ROOT = `${import.meta.dir}/..`;

const APPS_WITH_ENV = ["apps/api", "apps/web"];

for (const app of APPS_WITH_ENV) {
  const target = `${ROOT}/${app}/.env`;

  if (await Bun.file(target).exists()) {
    console.log(`${app}/.env already exists, kept.`);
    continue;
  }

  await copyFile(`${ROOT}/${app}/.env.example`, target);
  console.log(`${app}/.env created from .env.example.`);
}

await $`uv sync --all-packages --locked`.cwd(ROOT);
