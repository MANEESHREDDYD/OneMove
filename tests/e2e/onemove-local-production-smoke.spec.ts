import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Local Production Smoke Tests', () => {
  
  test.describe('Customer Role', () => {
    test.use({ storageState: path.join(__dirname, '../../playwright/.auth/customer.json') });
    
    test('Customer dashboard loads without 500 error', async ({ page }) => {
      await page.goto('/customer/rides');
      await expect(page.locator('h3').filter({ hasText: 'Where to?' })).toBeVisible();
      
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });

    test('Customer orders page loads', async ({ page }) => {
      await page.goto('/customer/orders');
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });
  });

  test.describe('Merchant Role', () => {
    test.use({ storageState: path.join(__dirname, '../../playwright/.auth/merchant.json') });
    
    test('Merchant dashboard loads', async ({ page }) => {
      await page.goto('/merchant');
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });
  });

  test.describe('Partner Role', () => {
    test.use({ storageState: path.join(__dirname, '../../playwright/.auth/partner.json') });
    
    test('Partner dashboard loads', async ({ page }) => {
      await page.goto('/driver');
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });
  });

  test.describe('Admin Role', () => {
    test.use({ storageState: path.join(__dirname, '../../playwright/.auth/admin.json') });
    
    test('Admin Architecture page loads', async ({ page }) => {
      await page.goto('/admin/architecture');
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });

    test('Admin Command Center page loads', async ({ page }) => {
      await page.goto('/admin/command-center');
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });

    test('Admin MLOps page loads', async ({ page }) => {
      await page.goto('/admin/mlops');
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });

    test('Admin Experiments page loads', async ({ page }) => {
      await page.goto('/admin/experiments');
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });
  });

  test.describe('Public Pages', () => {
    test('Showcase page loads', async ({ page }) => {
      await page.goto('/showcase');
      const bodyText = await page.textContent('body');
      expect(bodyText).not.toContain('500 Internal Server Error');
    });
  });
});
