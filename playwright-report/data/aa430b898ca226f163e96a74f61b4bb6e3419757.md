# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-error-handling.spec.ts >> OneMove Chaos & Error Handling >> Network offline during checkout handles gracefully
- Location: tests\e2e\onemove-error-handling.spec.ts:19:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('button').filter({ hasText: /Add \$/ }).first()

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e3]:
    - generic [ref=e4]:
      - generic [ref=e5]:
        - heading "Welcome back" [level=1] [ref=e6]
        - paragraph [ref=e7]: Enter your credentials to sign in to OneMove
      - generic [ref=e8]:
        - generic [ref=e9]:
          - generic [ref=e10]: Email
          - textbox "Email" [ref=e11]:
            - /placeholder: name@example.com
        - generic [ref=e12]:
          - generic [ref=e13]: Password
          - textbox "Password" [ref=e14]
        - button "Sign In" [ref=e15]
      - generic [ref=e16]:
        - text: Don't have an account?
        - link "Register here" [ref=e17] [cursor=pointer]:
          - /url: /auth/register
    - generic [ref=e19]:
      - paragraph [ref=e21]: Quick Demo Access
      - generic [ref=e23]:
        - button "Login as Customer" [ref=e24]:
          - img [ref=e25]
          - paragraph [ref=e28]: Login as Customer
        - button "Login as Partner / Driver" [ref=e29]:
          - img [ref=e30]
          - paragraph [ref=e35]: Login as Partner / Driver
        - button "Login as Merchant" [ref=e36]:
          - img [ref=e37]
          - paragraph [ref=e41]: Login as Merchant
        - button "Login as Admin" [ref=e42]:
          - img [ref=e43]
          - paragraph [ref=e45]: Login as Admin
  - region "Notifications alt+T"
  - alert [ref=e46]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('OneMove Chaos & Error Handling', () => {
  4  |   test('Invalid Order ID should gracefully handle missing data', async ({ page }) => {
  5  |     // Navigate directly to a non-existent order
  6  |     await page.goto('http://localhost:3000/auth/login');
  7  |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  8  |     await page.fill('input[type="password"]', 'Customer@001Move');
  9  |     await page.click('button[type="submit"]');
  10 |     await page.waitForURL('**/customer**');
  11 |     
  12 |     // Go to bad ID
  13 |     await page.goto('http://localhost:3000/customer/orders/invalid-uuid-1234');
  14 |     
  15 |     // It should either redirect to a 404/not-found or display a friendly error, not a white screen/runtime crash
  16 |     await expect(page.locator('text=not found').or(page.locator('text=Invalid order'))).toBeVisible();
  17 |   });
  18 |   
  19 |   test('Network offline during checkout handles gracefully', async ({ page, context }) => {
  20 |     await page.goto('http://localhost:3000/auth/login');
  21 |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  22 |     await page.fill('input[type="password"]', 'Customer@001Move');
  23 |     await page.click('button[type="submit"]');
  24 |     await page.waitForURL('**/customer**');
  25 | 
  26 |     // Add item and checkout
  27 |     await page.goto('http://localhost:3000/customer/eats');
  28 |     await page.click('a[href^="/customer/eats/"]');
> 29 |     await page.locator('button', { hasText: /Add \$/ }).first().click();
     |                                                                 ^ Error: locator.click: Test timeout of 30000ms exceeded.
  30 |     await page.click('text=View Cart & Checkout');
  31 |     
  32 |     await page.waitForURL(/.*\/customer\/checkout/);
  33 |     await page.locator('button', { hasText: 'Demo Wallet' }).click();
  34 |     
  35 |     // Go offline
  36 |     await context.setOffline(true);
  37 |     
  38 |     // Attempt checkout
  39 |     // UI might hang, throw error, or show toast. The key is no complete unhandled crash.
  40 |     await page.click('text=Place Order');
  41 |     
  42 |     // We expect some form of failure or it just doesn't proceed. We wait a bit.
  43 |     await page.waitForTimeout(2000);
  44 |     // Still on checkout page
  45 |     await expect(page).toHaveURL(/.*\/customer\/checkout/);
  46 |     
  47 |     // Go back online
  48 |     await context.setOffline(false);
  49 |   });
  50 | });
  51 | 
```