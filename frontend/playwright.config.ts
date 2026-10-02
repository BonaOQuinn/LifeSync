import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: { baseURL: 'http://127.0.0.1:5174', channel: process.env.PLAYWRIGHT_CHANNEL ?? 'msedge', headless: true, viewport: { width: 1440, height: 1000 }, trace: 'retain-on-failure' },
  reporter: 'list',
  webServer: [
    { command: 'python -m app.e2e_server', cwd: '../backend', url: 'http://127.0.0.1:8001/api/health', reuseExistingServer: false, timeout: 30000 },
    { command: 'npm run dev -- --port 5174', url: 'http://127.0.0.1:5174', env: { LIFESYNC_BACKEND_URL: 'http://127.0.0.1:8001' }, reuseExistingServer: false, timeout: 30000 },
  ],
})
