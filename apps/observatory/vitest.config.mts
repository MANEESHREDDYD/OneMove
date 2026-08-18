import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    // Playwright specs live in tests/e2e and are driven by a separate runner.
    include: ["src/**/*.test.{ts,tsx}"],
    restoreMocks: true,
    // Mounting a full page into jsdom costs seconds, and several suites doing
    // it at once on a shared CI runner pushes past the 5s default. These are
    // not slow tests; they are contended ones.
    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
});
