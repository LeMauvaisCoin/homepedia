import { parseClientEnv } from "./env-schema";

export const env = parseClientEnv(import.meta.env);
