# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-local-production-smoke.spec.ts >> Local Production Smoke Tests >> Customer Role >> Customer dashboard loads without 500 error
- Location: tests\e2e\onemove-local-production-smoke.spec.ts:9:9

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('h3').filter({ hasText: 'Where to?' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('h3').filter({ hasText: 'Where to?' })

```

```yaml
- heading "Welcome back" [level=1]
- paragraph: Enter your credentials to sign in to OneMove
- text: Email
- textbox "Email":
  - /placeholder: name@example.com
- text: Password
- textbox "Password"
- button "Sign In"
- text: Don't have an account?
- link "Register here":
  - /url: /auth/register
- paragraph: Quick Demo Access
- button "Login as Customer":
  - paragraph: Login as Customer
- button "Login as Partner / Driver":
  - paragraph: Login as Partner / Driver
- button "Login as Merchant":
  - paragraph: Login as Merchant
- button "Login as Admin":
  - paragraph: Login as Admin
- region "Notifications alt+T"
- alert
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import path from 'path';
  3  | 
  4  | test.describe('Local Production Smoke Tests', () => {
  5  |   
  6  |   test.describe('Customer Role', () => {
  7  |     test.use({ storageState: path.join(__dirname, '../../playwright/.auth/customer.json') });
  8  |     
  9  |     test('Customer dashboard loads without 500 error', async ({ page }) => {
  10 |       await page.goto('/customer/rides');
> 11 |       await expect(page.locator('h3').filter({ hasText: 'Where to?' })).toBeVisible();
     |                                                                         ^ Error: expect(locator).toBeVisible() failed
  12 |       
  13 |       const bodyText = await page.textContent('body');
  14 |       expect(bodyText).not.toContain('500 Internal Server Error');
  15 |     });
  16 | 
  17 |     test('Customer orders page loads', async ({ page }) => {
  18 |       await page.goto('/customer/orders');
  19 |       const bodyText = await page.textContent('body');
  20 |       expect(bodyText).not.toContain('500 Internal Server Error');
  21 |     });
  22 |   });
  23 | 
  24 |   test.describe('Merchant Role', () => {
  25 |     test.use({ storageState: path.join(__dirname, '../../playwright/.auth/merchant.json') });
  26 |     
  27 |     test('Merchant dashboard loads', async ({ page }) => {
  28 |       await page.goto('/merchant');
  29 |       const bodyText = await page.textContent('body');
  30 |       expect(bodyText).not.toContain('500 Internal Server Error');
  31 |     });
  32 |   });
  33 | 
  34 |   test.describe('Partner Role', () => {
  35 |     test.use({ storageState: path.join(__dirname, '../../playwright/.auth/partner.json') });
  36 |     
  37 |     test('Partner dashboard loads', async ({ page }) => {
  38 |       await page.goto('/driver');
  39 |       const bodyText = await page.textContent('body');
  40 |       expect(bodyText).not.toContain('500 Internal Server Error');
  41 |     });
  42 |   });
  43 | 
  44 |   test.describe('Admin Role', () => {
  45 |     test.use({ storageState: path.join(__dirname, '../../playwright/.auth/admin.json') });
  46 |     
  47 |     test('Admin Architecture page loads', async ({ page }) => {
  48 |       await page.goto('/admin/architecture');
  49 |       const bodyText = await page.textContent('body');
  50 |       expect(bodyText).not.toContain('500 Internal Server Error');
  51 |     });
  52 | 
  53 |     test('Admin Command Center page loads', async ({ page }) => {
  54 |       await page.goto('/admin/command-center');
  55 |       const bodyText = await page.textContent('body');
  56 |       expect(bodyText).not.toContain('500 Internal Server Error');
  57 |     });
  58 | 
  59 |     test('Admin MLOps page loads', async ({ page }) => {
  60 |       await page.goto('/admin/mlops');
  61 |       const bodyText = await page.textContent('body');
  62 |       expect(bodyText).not.toContain('500 Internal Server Error');
  63 |     });
  64 | 
  65 |     test('Admin Experiments page loads', async ({ page }) => {
  66 |       await page.goto('/admin/experiments');
  67 |       const bodyText = await page.textContent('body');
  68 |       expect(bodyText).not.toContain('500 Internal Server Error');
  69 |     });
  70 |   });
  71 | 
  72 |   test.describe('Public Pages', () => {
  73 |     test('Showcase page loads', async ({ page }) => {
  74 |       await page.goto('/showcase');
  75 |       const bodyText = await page.textContent('body');
  76 |       expect(bodyText).not.toContain('500 Internal Server Error');
  77 |     });
  78 |   });
  79 | });
  80 | 
```