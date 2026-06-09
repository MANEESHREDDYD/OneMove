import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Map Rendering and Local Production Smoke Tests', () => {
  // Use customer storage state
  test.use({ storageState: path.join(__dirname, '../../playwright/.auth/customer.json') });

  test('Leaflet map renders correctly on /customer/rides', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => {
      errors.push(error.message);
    });
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/customer/rides');
    
    // Wait for map container to be visible
    const mapContainer = page.locator('.leaflet-container');
    await expect(mapContainer).toBeVisible({ timeout: 10000 });
    
    // Ensure tiles are loaded
    const tiles = page.locator('img.leaflet-tile');
    await expect(tiles.first()).toBeVisible({ timeout: 10000 });
    
    // Ensure no _leaflet_pos or hydration errors
    const hasLeafletPosError = errors.some(e => e.includes('_leaflet_pos'));
    const hasHydrationError = errors.some(e => e.includes('Hydration') || e.toLowerCase().includes('window is not defined'));
    
    expect(hasLeafletPosError).toBe(false);
    expect(hasHydrationError).toBe(false);
    
    // Expect no generic 500
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('500 Internal Server Error');
  });
});
