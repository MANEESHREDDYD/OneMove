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
    // Wait for authentication to complete before navigating, otherwise the
    // protected route redirects back to /auth/login.
    await page.waitForURL(/.*\/customer/);

    await page.goto('http://localhost:3000/customer/rides');
    
    await page.fill('input[placeholder*="Where from?"]', 'JFK');
    await page.click('text=JFK Airport');
    
    await page.fill('input[placeholder*="Where to?"]', 'Times');
    await page.click('text=Times Square');
    
    await page.waitForSelector('text=Select a Ride');
    await page.getByText('Economy', { exact: true }).first().click();
    await page.getByRole('button', { name: 'Demo Wallet' }).click();

    const confirmButton = page.locator('button', { hasText: 'Request Economy' });
    await expect(confirmButton).toBeEnabled();

    await confirmButton.click();

    // Booking shows a success state then redirects after a short delay.
    await expect(page).toHaveURL(/.*\/customer\/rides\/.+/, { timeout: 15000 });
  });

  // Test 3: Eats Flow
  test('Customer can add food and checkout', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    // Wait for authentication to complete before navigating.
    await page.waitForURL(/.*\/customer/);

    await page.goto('http://localhost:3000/customer/eats');
    
    // Click the first restaurant link
    await page.waitForSelector('a[href^="/customer/eats/"]');
    await page.click('a[href^="/customer/eats/"]');
    
    // Ensure the menu detail page loads (items render with an add "+" button)
    await page.waitForSelector('button:has(.lucide-plus)');

    // Add the first menu item to the cart (icon-only "+" button)
    const addButton = page.locator('button:has(.lucide-plus)').first();
    if (await addButton.isVisible()) {
      await addButton.click();

      // Proceed to checkout
      await page.click('text=Go to Checkout');
      await expect(page).toHaveURL(/.*\/customer\/checkout/);
      
      // Select demo wallet and Place Order
      await page.locator('button', { hasText: 'Demo Wallet' }).click();
      await page.click('text=Place Order');
      
      // Should land on order detail page
      await expect(page).toHaveURL(/.*\/customer\/orders\/.+/);
    }
  });

});
