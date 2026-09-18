import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { type Plugin, defineConfig, loadEnv } from "vite";
import { parseClientEnv } from "./src/env-schema.ts";

// Arrête `vite dev`, `vite build` et `vite preview` si une variable du mode
// courant manque. Dans un hook : les outils qui ne font que lire cette
// configuration (Knip) n'ont pas besoin d'un fichier .env.
const validateEnv: Plugin = {
  name: "homepedia:validate-env",
  configResolved(config) {
    parseClientEnv(loadEnv(config.mode, config.envDir || config.root, "VITE_"));
  },
};

export default defineConfig({
  plugins: [
    validateEnv,
    tanstackRouter({ target: "react", autoCodeSplitting: true }),
    react(),
    tailwindcss(),
  ],
  resolve: { alias: { "@": `${import.meta.dirname}/src` } },
  server: { port: 5173, strictPort: true },
  preview: { port: 4173, strictPort: true },
});
