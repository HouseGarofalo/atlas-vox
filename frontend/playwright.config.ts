import { defineConfig, devices } from '@playwright/test';

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './e2e',
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry failed tests to handle timing/race conditions with backend */
  retries: process.env.CI ? 2 : 2,
  /* Limit workers to reduce backend load from parallel requests */
  workers: process.env.CI ? 1 : 4,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [['html', { open: 'never' }], ['list']],
  /* Global timeout per test */
  timeout: 30000,
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL — Docker frontend on 3100, or dev server on 5173 */
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3100',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video on failure */
    video: 'retain-on-failure',

    /* Default navigation timeout */
    navigationTimeout: 15000,

    /* Default action timeout */
    actionTimeout: 10000,
  },

  /* Only test Chromium for speed — add more browsers for CI */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Don't auto-start dev server — we test against Docker or a running server */
  webServer: undefined,
});