import { defineConfig, devices } from "@playwright/test";

// Dedicated ports: the scenarios leave the `bun run dev` servers alone.
const API_URL = "http://127.0.0.1:8100";

const WEB_URL = "http://127.0.0.1:4173";

const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  reporter: isCI
    ? [["list"], ["html", { open: "never" }], ["github"]]
    : [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: WEB_URL,
    locale: "fr-FR",
    timezoneId: "Europe/Paris",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Needs the local database: `bun run supabase:start`.
      command:
        "uv run uvicorn homepedia_api.main:create_configured_app --factory --host 127.0.0.1 --port 8100",
      cwd: "../api",
      url: `${API_URL}/health/ready`,
      env: {
        ENVIRONMENT: "test",
        DATABASE_URL:
          process.env.DATABASE_URL ??
          "postgresql://postgres:postgres@127.0.0.1:55322/postgres",
        CORS_ALLOWED_ORIGINS: WEB_URL,
      },
      reuseExistingServer: !isCI,
      timeout: 60_000,
    },
    {
      command: "vite build && vite preview --host 127.0.0.1",
      url: WEB_URL,
      env: { VITE_API_URL: API_URL },
      reuseExistingServer: !isCI,
      timeout: 120_000,
    },
  ],
});
