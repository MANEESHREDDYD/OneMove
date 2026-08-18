import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  test: {
    environment: 'node',
    exclude: ['**/node_modules/**', '**/e2e/**', '**/*.spec.ts', '.next/**', 'apps/**'],
    alias: {
      '@': path.resolve(__dirname, './'),
    },
  },
})
