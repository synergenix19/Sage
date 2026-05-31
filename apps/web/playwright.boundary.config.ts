/**
 * Separate Playwright config for boundary proof tests — no globalSetup.
 * Tests create their own auth contexts via signInAs() and don't need pre-stored cookies.
 */
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './playwright',
  testMatch: '**/middleware-boundary-proof.spec.ts',
  fullyParallel: false,
  retries: 0,
  timeout: 60_000,
  // No globalSetup — each test authenticates in its own fresh context
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
