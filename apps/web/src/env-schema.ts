import { createEnv } from "@t3-oss/env-core";
import { z } from "zod";

type RuntimeEnv = Record<string, string | boolean | number | undefined>;

// Shared between the browser (src/env.ts) and build-time validation
// (vite.config.ts). Public values only: they end up in the bundle.
export function parseClientEnv(runtimeEnv: RuntimeEnv) {
  return createEnv({
    clientPrefix: "VITE_",
    client: {
      VITE_API_URL: z.union([z.url(), z.literal("/api")]),
    },
    runtimeEnv,
    emptyStringAsUndefined: true,
  });
}
