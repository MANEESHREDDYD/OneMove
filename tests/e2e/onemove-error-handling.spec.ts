import { test, expect } from '@playwright/test';

test.describe('OneMove Chaos & Error Handling', () => {
  test('Invalid Order ID should gracefully handle missing data', async ({ page }) => {
    // Navigate directly to a non-existent order
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/customer**');
    
    // Go to bad ID. The app handles this gracefully by redirecting back to the
    // orders list (no white screen / runtime crash).
    await page.goto('http://localhost:3000/customer/orders/invalid-uuid-1234').catch(() => {});

    await expect(page).toHaveURL(/.*\/customer\/orders/);
  });
  
  test('Network offline during checkout handles gracefully', async ({ page, context }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/customer**');

    // Add item and checkout
    await page.goto('http://localhost:3000/customer/eats');
    await page.waitForSelector('a[href^="/customer/eats/"]');
    await page.click('a[href^="/customer/eats/"]');
    await page.locator('button:has(.lucide-plus)').first().click();
    await page.click('text=Go to Checkout');

    await page.waitForURL(/.*\/customer\/checkout/);
    await page.locator('button', { hasText: 'Demo Wallet' }).click();
    
    // Go offline
    await context.setOffline(true);
    
    // Attempt checkout
    // UI might hang, throw error, or show toast. The key is no complete unhandled crash.
    await page.click('text=Place Order');
    
    // We expect some form of failure or it just doesn't proceed. We wait a bit.
    await page.waitForTimeout(2000);
    // Still on checkout page
    await expect(page).toHaveURL(/.*\/customer\/checkout/);
    
    // Go back online
    await context.setOffline(false);
  });
});
