import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { execFileSync } from "node:child_process";
import { type Plugin, defineConfig, loadEnv } from "vite";
import { parseClientEnv } from "./src/env-schema.ts";

// Arrête `vite dev`, `vite build` et `vite preview` si une variable du mode
// courant manque. Dans un hook : les outils qui ne font que lire cette
// configuration (Knip) n'ont pas besoin d'un fichier .env.
const validateEnv: Plugin = {
  name: "homepedia:validate-env",
  configResolved(config) {
    parseClientEnv(config.env);
  },
};

export default defineConfig(({ command, isPreview, mode }) => {
  const portlessDev =
    command === "serve" && !isPreview && Boolean(process.env.PORTLESS_URL);

  const devEnv = loadEnv(mode, import.meta.dirname, "DEV_");

  const apiTarget = portlessDev
    ? process.env.DEV_API_URL ||
      devEnv.DEV_API_URL ||
      execFileSync("portless", ["get", "api.homepedia"], {
        encoding: "utf8",
      }).trim()
    : undefined;

  return {
    plugins: [
      portlessDev
        ? {
            name: "homepedia:dev-api",
            configResolved(config) {
              config.env.VITE_API_URL = "/api";
            },
          }
        : undefined,
      validateEnv,
      tanstackRouter({ target: "react", autoCodeSplitting: true }),
      react(),
      tailwindcss(),
    ],
    resolve: { alias: { "@": `${import.meta.dirname}/src` } },
    server: {
      port: 5173,
      strictPort: true,
      allowedHosts:
        portlessDev && process.env.PORTLESS_TAILSCALE_URL
          ? [new URL(process.env.PORTLESS_TAILSCALE_URL).hostname]
          : [],
      proxy: apiTarget
        ? {
            "/api": {
              target: apiTarget,
              changeOrigin: true,
              rewrite: (path) => path.replace(/^\/api/, ""),
            },
          }
        : undefined,
    },
    preview: { port: 4173, strictPort: true },
  };
});
