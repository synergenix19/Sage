import { defineConfig, devices } from '@playwright/test'
import path from 'path'

export default defineConfig({
  testDir: './playwright',
  fullyParallel: false, // session lifecycle tests must not interfere with each other
  retries: 0,
  timeout: 30_000,
  globalSetup: path.resolve(__dirname, './playwright/global-setup.ts'),
  use: {
    baseURL: 'http://localhost:3000',
    storageState: path.resolve(__dirname, './playwright/.auth-state.json'),
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
