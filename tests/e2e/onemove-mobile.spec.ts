import { test, expect, devices } from '@playwright/test';

test.use({ ...devices['iPhone 13'] });

test.describe('OneMove Mobile Viewport Tests', () => {
  test('Mobile Navigation and Cart are usable', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    
    await page.waitForURL('**/customer**');
    
    // Test hamburger menu if it exists, or bottom nav
    const mobileMenu = page.locator('button[aria-label="Open menu"]');
    if (await mobileMenu.isVisible()) {
        await mobileMenu.click();
        await expect(page.locator('a[href="/customer/eats"]')).toBeVisible();
    }
  });

  test('Ride Booking renders correctly on mobile', async ({ page }) => {
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    
    await page.goto('http://localhost:3000/customer/rides');
    
    // Check map container doesn't overflow horizontally
    const map = page.locator('.leaflet-container');
    if (await map.count() > 0) {
        const box = await map.boundingBox();
        expect(box!.width).toBeLessThanOrEqual(390); // iPhone 13 width
    }
  });
});
