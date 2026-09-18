import { expect, test } from "bun:test";
import { parseClientEnv } from "./env-schema";

test("accepts a valid API URL", () => {
  const env = parseClientEnv({ VITE_API_URL: "http://localhost:8000" });

  expect(env.VITE_API_URL).toBe("http://localhost:8000");
});

test("rejects a missing API URL", () => {
  expect(() => parseClientEnv({})).toThrow("Invalid environment variables");
});

test("treats an empty API URL as missing", () => {
  expect(() => parseClientEnv({ VITE_API_URL: "" })).toThrow(
    "Invalid environment variables",
  );
});
