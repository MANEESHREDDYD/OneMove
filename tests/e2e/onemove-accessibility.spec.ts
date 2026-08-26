import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// The routes requested for F-028 certification
const ROUTES = [
  '/',
  '/auth/login',
  '/executive',
  '/network',
  '/admin/system-health',
  '/admin/analytics', // data-health equivalent
  '/admin/rides',     // representative admin surface
];

test.describe('OneMove Accessibility (A11y) Gate - F-028', () => {
  test('Application surfaces must have 0 critical and 0 serious violations', async ({ page }) => {
    // Authenticate once
    await page.goto('http://localhost:3000/auth/login');
    await page.fill('input[type="email"]', 'customer001@onemove.demo');
    await page.fill('input[type="password"]', 'Customer@001Move');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/customer**');

    for (const route of ROUTES) {
      await test.step(`Check ${route}`, async () => {
        await page.goto(`http://localhost:3000${route}`);
        await page.waitForLoadState('networkidle');

        const accessibilityScanResults = await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .analyze();

        const criticalViolations = accessibilityScanResults.violations.filter(v => v.impact === 'critical');
        const seriousViolations = accessibilityScanResults.violations.filter(v => v.impact === 'serious');
        
        if (criticalViolations.length > 0 || seriousViolations.length > 0) {
          console.error(`A11y Violations on ${route}:`);
          console.error('Critical:', JSON.stringify(criticalViolations, null, 2));
          console.error('Serious:', JSON.stringify(seriousViolations, null, 2));
        }

        expect(criticalViolations.length, `Expected 0 critical violations on ${route}`).toBe(0);
        expect(seriousViolations.length, `Expected 0 serious violations on ${route}`).toBe(0);
      });
    }
  });
});
