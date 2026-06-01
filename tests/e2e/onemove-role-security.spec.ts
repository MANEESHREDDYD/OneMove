import { test, expect } from '@playwright/test';

test.describe('OneMove E2E Role Security', () => {
  test('Customer cannot access admin or merchant routes', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    
    await page.waitForURL('**/customer**');
    
    // Attempt Admin Access
    await page.goto('http://localhost:3000/admin/command-center');
    await expect(page).toHaveURL(/.*\/customer|.*\/auth\/login/); // Should bounce
    
    // Attempt Merchant Access
    await page.goto('http://localhost:3000/merchant');
    await expect(page).toHaveURL(/.*\/customer|.*\/auth\/login/); // Should bounce
  });
  
  test('Partner cannot access admin', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'partner001@onemove.demo');
    await page.fill('input[type="password"]', 'Partner@001Move');
    await page.click('button[type="submit"]');
    
    await page.waitForURL('**/partner**');
    
    // Attempt Admin Access
    await page.goto('http://localhost:3000/admin/command-center');
    await expect(page).toHaveURL(/.*\/partner|.*\/auth\/login/); // Should bounce
  });
});
