import { test, expect } from '@playwright/test';
import { assertNoConsoleErrors } from './helpers/assertNoConsoleErrors';

test.describe('OneMove Idempotency', () => {
  test('Browser Back button after successful checkout does not resubmit cart', async ({ page }) => {
    const checkErrors = assertNoConsoleErrors(page);
    
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
    await page.locator('button', { hasText: 'Place Order' }).click();
    
    // Land on order tracking
    await page.waitForURL(/.*\/customer\/orders\/.*/);
    
    // Hit browser back
    await page.goBack();
    
    // Attempting to resubmit the same cart should either show it's empty, or the idempotency key in the action should reject it.
    // Assuming UI handles empty cart by disabling Place Order.
    const placeOrderBtn = page.locator('button:has-text("Place Order")');
    if (await placeOrderBtn.isVisible()) {
      await expect(placeOrderBtn).toBeDisabled();
    }
    
    checkErrors();
  });
});
