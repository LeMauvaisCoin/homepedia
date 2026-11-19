import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { execFileSync } from "node:child_process";
import { type Plugin, defineConfig, loadEnv } from "vite";
import { parseClientEnv } from "./src/env-schema.ts";

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
      // WARNING: Tailscale cuts a silent WebSocket after 10 s; the 30 s HMR default caused a reload loop.
      hmr: { timeout: 5000 },
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
