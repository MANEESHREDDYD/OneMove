# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-idempotency.spec.ts >> OneMove Idempotency >> Browser Back button after successful checkout does not resubmit cart
- Location: tests\e2e\onemove-idempotency.spec.ts:5:7

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
        - link "Register here" [ref=e17]:
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
  2  | import { assertNoConsoleErrors } from './helpers/assertNoConsoleErrors';
  3  | 
  4  | test.describe('OneMove Idempotency', () => {
  5  |   test('Browser Back button after successful checkout does not resubmit cart', async ({ page }) => {
  6  |     const checkErrors = assertNoConsoleErrors(page);
  7  |     
  8  |     await page.goto('http://localhost:3000/auth/login');
  9  |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  10 |     await page.fill('input[type="password"]', 'Customer@001Move');
  11 |     await page.click('button[type="submit"]');
  12 |     
  13 |     await page.waitForURL('**/customer**');
  14 |     
  15 |     // Add item and checkout
  16 |     await page.goto('http://localhost:3000/customer/eats');
  17 |     await page.click('a[href^="/customer/eats/"]');
> 18 |     await page.locator('button', { hasText: /Add \$/ }).first().click();
     |                                                                 ^ Error: locator.click: Test timeout of 30000ms exceeded.
  19 |     await page.click('text=View Cart & Checkout');
  20 |     
  21 |     await page.waitForURL(/.*\/customer\/checkout/);
  22 |     await page.locator('button', { hasText: 'Demo Wallet' }).click();
  23 |     await page.locator('button', { hasText: 'Place Order' }).click();
  24 |     
  25 |     // Land on order tracking
  26 |     await page.waitForURL(/.*\/customer\/orders\/.*/);
  27 |     
  28 |     // Hit browser back
  29 |     await page.goBack();
  30 |     
  31 |     // Attempting to resubmit the same cart should either show it's empty, or the idempotency key in the action should reject it.
  32 |     // Assuming UI handles empty cart by disabling Place Order.
  33 |     const placeOrderBtn = page.locator('button:has-text("Place Order")');
  34 |     if (await placeOrderBtn.isVisible()) {
  35 |       await expect(placeOrderBtn).toBeDisabled();
  36 |     }
  37 |     
  38 |     checkErrors();
  39 |   });
  40 | });
  41 | 
```