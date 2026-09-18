// Prépare une copie neuve : fichiers .env locaux et environnement Python.
import { copyFile } from "node:fs/promises";
import { $ } from "bun";

const ROOT = `${import.meta.dir}/..`;

const APPS_WITH_ENV = ["apps/api", "apps/web"];

for (const app of APPS_WITH_ENV) {
  const target = `${ROOT}/${app}/.env`;

  if (await Bun.file(target).exists()) {
    console.log(`${app}/.env existe déjà, conservé.`);
    continue;
  }

  await copyFile(`${ROOT}/${app}/.env.example`, target);
  console.log(`${app}/.env créé depuis .env.example.`);
}

await $`uv sync --all-packages --locked`.cwd(ROOT);
