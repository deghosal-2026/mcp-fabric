import { defineConfig, devices } from '@playwright/test'

const isLiveDocker = process.env.PLAYWRIGHT_LIVE_DOCKER === '1'
const baseURL = isLiveDocker
  ? process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000'
  : process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:4173'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: '../docs/ui-test/findings/playwright-report' }],
  ],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: isLiveDocker
    ? undefined
    : {
        command: 'npm run build && npm run preview',
        url: 'http://localhost:4173',
        reuseExistingServer: !process.env.CI,
        timeout: 30000,
      },
})
