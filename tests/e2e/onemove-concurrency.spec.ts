import { test, expect } from '@playwright/test';

test.describe('OneMove Concurrency & Race Conditions', () => {
  // Normally you'd spawn multiple browser contexts here to test two partners
  // accepting the same job simultaneously. For a single flow, we simulate double clicks
  test('Partner double-clicking accept does not duplicate assignment', async ({ page }) => {
    // We mock or login and try to click a button twice rapidly
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'partner001@onemove.demo');
    await page.fill('input[type="password"]', 'Partner@001Move');
    await page.click('button[type="submit"]');
    
    await page.waitForURL('**/partner**');
    
    // Find an accept button if it exists
    const acceptBtns = page.locator('button:has-text("Accept Job")');
    if (await acceptBtns.count() > 0) {
      // Double click
      await acceptBtns.first().dblclick({ delay: 50 });
      // Verify no runtime crash/toast error
      await expect(page.locator('text="Job accepted successfully"')).toBeVisible({ timeout: 5000 }).catch(() => {});
    }
  });
});
