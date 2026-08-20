import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: /swiggy-friday-demo\.spec\.ts/,
  fullyParallel: false,
  reporter: [['list'], ['json', { outputFile: 'playwright-report/demo-results.json' }]],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on',
    video: 'on',
    screenshot: 'only-on-failure',
    viewport: { width: 1920, height: 1080 }
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    }
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120000,
  },
});
