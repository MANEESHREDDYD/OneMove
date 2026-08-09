import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores([
    "**/.next/**",
    "**/out/**",
    "**/build/**",
    "**/.turbo/**",
    "**/next-env.d.ts",
    "**/Assist/**",
    "**/python/**",
    "**/java/**",
    "**/c/**",
    "**/data/**",
    "**/data_root/**",
    "**/private/**",
    "**/playwright-report/**",
    "**/test-results/**",
    "**/coverage/**",
    "**/*.ps1",
    "**/node_modules/**"
  ]),
  {
    files: [
      "**/scripts/**/*",
      "**/tests/**/*",
      "**/lib/**/*",
      "**/app/**/*",
      "**/components/**/*",
      "**/legacy_demo/**/*",
      "**/*.config.*"
    ],
    ignores: [
      "**/node_modules/**",
      "**/.next/**",
      "**/out/**",
      "**/build/**",
      "**/.turbo/**",
      "**/playwright-report/**",
      "**/test-results/**",
      "**/coverage/**",
      "**/.supabase/**",
      "**/supabase/.temp/**",
      "**/.cache/**",
      "**/data_root/**"
    ],
    rules: {
      "@typescript-eslint/no-require-imports": "off",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unsafe-function-type": "off",
      "@typescript-eslint/no-empty-object-type": "off",
      "@typescript-eslint/no-unused-vars": "off"
    },
  },
]);

export default eslintConfig;
