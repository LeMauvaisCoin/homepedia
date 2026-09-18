import { createEnv } from "@t3-oss/env-core";
import { z } from "zod";

type RuntimeEnv = Record<string, string | boolean | number | undefined>;

// Partagé entre le navigateur (src/env.ts) et la validation au build
// (vite.config.ts). Seules des valeurs publiques : elles finissent dans le bundle.
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
