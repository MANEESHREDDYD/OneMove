import { test, expect } from '@playwright/test';

test('network map renders authentic H3 cells', async ({ page }) => {
  await page.goto('/network');
  await page.waitForSelector('svg[role="img"]', { timeout: 30000 });
  const polys = await page.locator('svg[role="img"] polygon').count();
  console.log('POLYGONS_RENDERED=' + polys);
  expect(polys).toBeGreaterThan(50);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'artifacts/swiggy-demo/final/screenshots/01-network.png', fullPage: false });
});
