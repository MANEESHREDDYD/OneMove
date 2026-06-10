import { test, expect } from '@playwright/test';

test.describe('OneMove Session Hardening & Stale State', () => {
  test('Cross-tab sign-out logs out all tabs and blocks back-button caching', async ({ browser }) => {
    const context = await browser.newContext();
    const tab1 = await context.newPage();
    
    // Login on tab 1
    await tab1.goto('http://localhost:3000/auth/login');
    await tab1.fill('input[type="email"]', 'customer001@onemove.demo');
    await tab1.fill('input[type="password"]', 'Customer@001Move');
    await tab1.click('button[type="submit"]');
    await tab1.waitForURL('**/customer**');
    
    // Open tab 2 and verify we are logged in (the protected route renders
    // instead of bouncing to login).
    const tab2 = await context.newPage();
    await tab2.goto('http://localhost:3000/customer/eats');
    await expect(tab2).toHaveURL(/.*\/customer\/eats/);
    
    // Sign out on tab 1
    await tab1.click('text="Sign Out"');
    await tab1.waitForURL('**/auth/login');
    
    // Attempt an action on tab 2 without refreshing (should fail/redirect due to server action checking auth)
    // We'll simulate a navigation request since JS might still be loaded
    await tab2.goto('http://localhost:3000/customer/rides');
    await tab2.waitForURL('**/auth/login'); // Auth check middleware must bounce us
    
    // Attempt to use browser back button on tab 1
    await tab1.goBack();
    // It might load from bfcache, but any server interaction should bounce, and middleware should prevent navigation
    await expect(tab1).toHaveURL(/.*\/auth\/login/);
  });
});
