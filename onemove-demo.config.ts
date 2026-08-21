import { defineConfig, devices } from '@playwright/test';

/**
 * Recording configuration for the network-intelligence walkthrough.
 *
 * The viewport and video size are re-asserted AFTER the device spread:
 * devices['Desktop Chrome'] carries its own 1280x720 and silently downgraded
 * every earlier recording to 720p.
 */
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: /onemove-network-intelligence\.spec\.ts/,
  fullyParallel: false,
  timeout: 900_000,
  expect: { timeout: 30_000 },
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'off',
    video: 'on',
    screenshot: 'off',
    viewport: { width: 1920, height: 1080 },
  },
  projects: [
    {
      name: 'record',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
        video: { mode: 'on', size: { width: 1920, height: 1080 } },
      },
    },
  ],
  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 180_000,
  },
});
