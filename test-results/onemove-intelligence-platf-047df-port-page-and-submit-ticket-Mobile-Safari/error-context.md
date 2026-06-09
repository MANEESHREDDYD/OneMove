# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-intelligence-platform-phase4.spec.ts >> Intelligence Platform Phase 4: Customer Support >> Customer can access support page and submit ticket
- Location: tests\e2e\onemove-intelligence-platform-phase4.spec.ts:51:7

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: locator('h1')
Expected substring: "Help & Support"
Received string:    "Welcome back"
Timeout: 5000ms

Call log:
  - Expect "toContainText" with timeout 5000ms
  - waiting for locator('h1')
    13 × locator resolved to <h1 class="text-3xl font-bold tracking-tight">Welcome back</h1>
       - unexpected value "Welcome back"

```

```yaml
- heading "Welcome back" [level=1]
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
  25 |     test.setTimeout(90000) // Increase timeout for simulation
  26 |     await page.goto('/admin/experiments')
  27 |     await expect(page.locator('h1')).toContainText('A/B Experiments Platform')
  28 |     
  29 |     // Check simulate button
  30 |     const simulateBtn = page.locator('button:has-text("Simulate Traffic")')
  31 |     await expect(simulateBtn).toBeVisible()
  32 |     
  33 |     // Trigger simulation
  34 |     await simulateBtn.click()
  35 |     
  36 |     // Page reloads and should show metrics instead of "No metrics collected yet"
  37 |     // The metric display has "Impressions", wait for it
  38 |     await expect(page.locator('text=Impressions').first()).toBeVisible({ timeout: 60000 })
  39 |   })
  40 | 
  41 |   test('Admin MLOps page loads', async ({ page }) => {
  42 |     await page.goto('/admin/mlops')
  43 |     await expect(page.locator('h1')).toContainText('MLOps Dashboard')
  44 |     await expect(page.locator('text=Pipeline Execution History')).toBeVisible()
  45 |   })
  46 | })
  47 | 
  48 | test.describe('Intelligence Platform Phase 4: Customer Support', () => {
  49 |   test.use({ storageState: 'playwright/.auth/customer.json' })
  50 | 
  51 |   test('Customer can access support page and submit ticket', async ({ page }) => {
  52 |     await page.goto('/customer/support')
> 53 |     await expect(page.locator('h1')).toContainText('Help & Support')
     |                                      ^ Error: expect(locator).toContainText(expected) failed
  54 |     
  55 |     // Fill out form
  56 |     await page.fill('textarea[name="description"]', 'My food arrived completely cold and late.')
  57 |     await page.click('button:has-text("Submit Ticket")')
  58 |     
  59 |     // It should reload and show the ticket
  60 |     await expect(page.locator('text=Help & Support')).toBeVisible()
  61 |   })
  62 | })
  63 | 
```