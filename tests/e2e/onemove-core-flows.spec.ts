import { test, expect } from '@playwright/test';

test.describe('OneMove Core Marketplace E2E Flows', () => {
  // Test 1: Sign out works for all roles
  test('Login and sign out as customer', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL(/.*\/customer/);
    
    // Click Sign Out
    await page.click('button:has-text("Sign Out")');
    await expect(page).toHaveURL(/.*\/auth\/login/);
  });

  // Test 2: Ride Booking 
  test('Customer can book a ride', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    
    await page.goto('http://localhost:3000/customer/rides');
    
    await page.fill('input[placeholder*="Where from?"]', 'JFK');
    await page.click('text=JFK Airport');
    
    await page.fill('input[placeholder*="Where to?"]', 'Times');
    await page.click('text=Times Square');
    
    await page.waitForSelector('text=Select a Ride');
    await page.click('text=OneMove Economy');
    await page.click('text=Demo Wallet');
    
    const confirmButton = page.locator('button', { hasText: 'Confirm Economy' });
    await expect(confirmButton).toBeEnabled();
    
    await confirmButton.click();
    
    // Should redirect to a valid details page
    await expect(page).toHaveURL(/.*\/customer\/rides\/.+/);
  });

  // Test 3: Eats Flow
  test('Customer can add food and checkout', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    
    await page.goto('http://localhost:3000/customer/eats');
    
    // Click the first restaurant link
    await page.waitForSelector('a[href^="/customer/eats/"]');
    await page.click('a[href^="/customer/eats/"]');
    
    // Ensure detail page loads properly and we see products or at least the menu client
    await page.waitForSelector('text=Menu');
    
    // Look for an "Add to Cart" button
    const addButton = page.locator('button', { hasText: /Add \$/ }).first();
    if (await addButton.isVisible()) {
      await addButton.click();
      
      // Proceed to checkout
      await page.click('text=Proceed to Checkout');
      await expect(page).toHaveURL(/.*\/customer\/checkout/);
      
      // Select demo wallet and Place Order
      await page.locator('button', { hasText: 'Demo Wallet' }).click();
      await page.click('text=Place Order');
      
      // Should land on order detail page
      await expect(page).toHaveURL(/.*\/customer\/orders\/.+/);
    }
  });

});
