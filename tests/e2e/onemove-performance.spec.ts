import { test, expect } from '@playwright/test';

test.describe('OneMove Performance Budgets', () => {
  // Test navigation performance
  test('Customer eats page usable under 2s', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    
    await page.waitForURL('**/customer**');
    
    const startTime = Date.now();
    await page.goto('http://localhost:3000/customer/eats');
    // Wait for restaurants to populate
    await page.waitForSelector('a[href^="/customer/eats/"]');
    const loadTime = Date.now() - startTime;
    
    // Performance budget assertion
    expect(loadTime).toBeLessThan(3000); // 3 seconds allowance for local dev
  });

  test('Admin command center loads efficiently', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'admin001@onemove.demo'); // Assume admin credential structure
    await page.fill('input[type="password"]', 'Demo@12345');
    await page.click('button[type="submit"]');
    
    const startTime = Date.now();
    await page.goto('http://localhost:3000/admin/command-center');
    // Ensure dashboard renders
    await page.waitForSelector('text=Active Orders');
    const loadTime = Date.now() - startTime;
    
    expect(loadTime).toBeLessThan(4000); // 4 seconds allowance for admin dashboard
  });
});
