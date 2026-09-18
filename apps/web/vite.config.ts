import tailwindcss from "@tailwindcss/vite";
import { tanstackRouter } from "@tanstack/router-plugin/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import { parseClientEnv } from "./src/env-schema.ts";

export default defineConfig(({ mode }) => {
  // Échoue dès `vite build` ou `vite dev` si une variable du mode courant manque.
  parseClientEnv(loadEnv(mode, import.meta.dirname, "VITE_"));

  return {
    plugins: [
      tanstackRouter({ target: "react", autoCodeSplitting: true }),
      react(),
      tailwindcss(),
    ],
    resolve: { alias: { "@": `${import.meta.dirname}/src` } },
    server: { port: 5173, strictPort: true },
    preview: { port: 4173, strictPort: true },
  };
});
