# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-intelligence-platform-phase4.spec.ts >> Intelligence Platform Phase 4: AI Assistants and MLOps >> Admin Experiments page loads and simulates data
- Location: tests\e2e\onemove-intelligence-platform-phase4.spec.ts:24:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: expect.toBeVisible: Target page, context or browser has been closed
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Intelligence Platform Phase 4: AI Assistants and MLOps', () => {
  4  |   test.use({ storageState: 'playwright/.auth/admin.json' })
  5  | 
  6  |   test('Admin Ops Assistant page loads and displays data', async ({ page }) => {
  7  |     await page.goto('/admin/ops-assistant')
  8  |     await expect(page.locator('h1')).toContainText('Admin Ops Assistant')
  9  |     await expect(page.locator('text=MVP deterministic rule-based intelligence')).toBeVisible()
  10 |     await expect(page.locator('text=Prioritized Action Items')).toBeVisible()
  11 |     
  12 |     // Check that there are no console errors
  13 |     const errors: string[] = []
  14 |     page.on('pageerror', err => errors.push(err.message))
  15 |     expect(errors.length).toBe(0)
  16 |   })
  17 | 
  18 |   test('Admin Support Desk page loads', async ({ page }) => {
  19 |     await page.goto('/admin/support-desk')
  20 |     await expect(page.locator('h1')).toContainText('AI Support Desk')
  21 |     await expect(page.locator('table')).toBeVisible()
  22 |   })
  23 | 
  24 |   test('Admin Experiments page loads and simulates data', async ({ page }) => {
  25 |     await page.goto('/admin/experiments')
  26 |     await expect(page.locator('h1')).toContainText('A/B Experiments Platform')
  27 |     
  28 |     // Check simulate button
  29 |     const simulateBtn = page.locator('button:has-text("Simulate Traffic")')
  30 |     await expect(simulateBtn).toBeVisible()
  31 |     
  32 |     // Trigger simulation
  33 |     await simulateBtn.click()
  34 |     
  35 |     // Page reloads and should show metrics
> 36 |     await expect(page.locator('text=A/B Experiments Platform')).toBeVisible()
     |                                                                 ^ Error: expect.toBeVisible: Target page, context or browser has been closed
  37 |   })
  38 | 
  39 |   test('Admin MLOps page loads', async ({ page }) => {
  40 |     await page.goto('/admin/mlops')
  41 |     await expect(page.locator('h1')).toContainText('MLOps Dashboard')
  42 |     await expect(page.locator('text=Pipeline Execution History')).toBeVisible()
  43 |   })
  44 | })
  45 | 
  46 | test.describe('Intelligence Platform Phase 4: Customer Support', () => {
  47 |   test.use({ storageState: 'playwright/.auth/customer.json' })
  48 | 
  49 |   test('Customer can access support page and submit ticket', async ({ page }) => {
  50 |     await page.goto('/customer/support')
  51 |     await expect(page.locator('h1')).toContainText('Help & Support')
  52 |     
  53 |     // Fill out form
  54 |     await page.fill('textarea[name="description"]', 'My food arrived completely cold and late.')
  55 |     await page.click('button:has-text("Submit Ticket")')
  56 |     
  57 |     // It should reload and show the ticket
  58 |     await expect(page.locator('text=Help & Support')).toBeVisible()
  59 |   })
  60 | })
  61 | 
```