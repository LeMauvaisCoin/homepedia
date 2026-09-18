// Prépare une copie neuve : fichiers .env locaux et environnement Python.
import { $ } from "bun";

const ROOT = `${import.meta.dir}/..`;

const APPS_WITH_ENV = ["apps/api", "apps/web"];

for (const app of APPS_WITH_ENV) {
  const target = Bun.file(`${ROOT}/${app}/.env`);

  if (await target.exists()) {
    console.log(`${app}/.env existe déjà, conservé.`);
    continue;
  }

  await Bun.write(target, Bun.file(`${ROOT}/${app}/.env.example`));
  console.log(`${app}/.env créé depuis .env.example.`);
}

await $`uv sync --all-packages --locked`.cwd(ROOT);
