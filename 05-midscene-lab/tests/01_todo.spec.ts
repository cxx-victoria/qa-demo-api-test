import { test, expect } from '@playwright/test';
import { PlaywrightAgent } from '@midscene/web/playwright';

test('用自然语言添加一条待办并校验', async ({ page }) => {
  await page.goto('https://demo.playwright.dev/todomvc');
  const agent = new PlaywrightAgent(page);

  await agent.aiAct('在顶部的输入框里输入 "买牛奶"，然后按回车');
  await agent.aiAssert('页面上出现了 "买牛奶" 这条待办事项');

  const first = await agent.aiQuery('string, 列表中第一条待办的文字');
  console.log('提取到的第一条待办：', first);
  expect(first).toContain('买牛奶');
});