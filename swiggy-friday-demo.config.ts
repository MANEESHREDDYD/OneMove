import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: /swiggy-friday-demo\.spec\.ts/,
  fullyParallel: false,
  // The demo is a paced 6-8 minute narrative with deliberate pauses at each step
  // plus real CP-SAT polling. Playwright's 30s default aborted it mid-journey.
  timeout: 900_000,
  expect: { timeout: 30_000 },
  reporter: [['list'], ['json', { outputFile: 'playwright-report/demo-results.json' }]],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on',
    video: 'on',
    screenshot: 'on',
    viewport: { width: 1920, height: 1080 }
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // devices['Desktop Chrome'] carries its own 1280x720 viewport and was
        // silently overriding the 1920x1080 set above, so every recording was
        // captured at 720p. Re-assert it AFTER the spread.
        viewport: { width: 1920, height: 1080 },
        video: { mode: 'on', size: { width: 1920, height: 1080 } },
      },
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
