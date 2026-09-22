import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',            // 用例放在 tests 目录
  timeout: 120_000,              // 每条用例超时 120 秒（AI 调用慢，要给足）
  expect: { timeout: 30_000 },
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],
  use: {
    headless: false,             // 先设为"有头"模式，方便肉眼观察 AI 的操作
    viewport: { width: 1280, height: 800 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
});