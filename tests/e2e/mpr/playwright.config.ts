import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const CAPTURAS = path.resolve(__dirname, '../../../docs/mpr/e2e/capturas');

export default defineConfig({
  testDir: '.',
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: path.join(__dirname, 'playwright-report'), open: 'never' }],
  ],
  use: {
    baseURL: process.env.SYNAP_BASE_URL || 'http://localhost:8000',
    trace: 'on-first-retry',
    screenshot: 'off',
    video: 'off',
    locale: 'es-AR',
    viewport: { width: 1440, height: 900 },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  outputDir: path.join(__dirname, 'test-results'),
});

export { CAPTURAS };
