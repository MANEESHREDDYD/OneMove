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
  },
});
