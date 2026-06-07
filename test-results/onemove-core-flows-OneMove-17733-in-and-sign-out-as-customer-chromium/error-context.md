# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-core-flows.spec.ts >> OneMove Core Marketplace E2E Flows >> Login and sign out as customer
- Location: tests\e2e\onemove-core-flows.spec.ts:5:7

# Error details

```
Error: expect(page).toHaveURL(expected) failed

Expected pattern: /.*\/customer/
Received string:  "http://localhost:3000/auth/login"
Timeout: 5000ms

Call log:
  - Expect "toHaveURL" with timeout 5000ms
    13 × unexpected value "http://localhost:3000/auth/login"

```

```yaml
- heading "Welcome back" [level=1]
- paragraph: Enter your credentials to sign in to OneMove
- text: Email
- textbox "Email":
  - /placeholder: name@example.com
  - text: customer001@onemove.demo
- text: Password
- textbox "Password": Customer@001Move
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
  2  | 
  3  | test.describe('OneMove Core Marketplace E2E Flows', () => {
  4  |   // Test 1: Sign out works for all roles
  5  |   test('Login and sign out as customer', async ({ page }) => {
  6  |     await page.goto('http://localhost:3000/auth/login');
  7  |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  8  |     await page.fill('input[type="password"]', 'Customer@001Move');
  9  |     await page.click('button[type="submit"]');
  10 |     
> 11 |     await expect(page).toHaveURL(/.*\/customer/);
     |                        ^ Error: expect(page).toHaveURL(expected) failed
  12 |     
  13 |     // Click Sign Out
  14 |     await page.click('button:has-text("Sign Out")');
  15 |     await expect(page).toHaveURL(/.*\/auth\/login/);
  16 |   });
  17 | 
  18 |   // Test 2: Ride Booking 
  19 |   test('Customer can book a ride', async ({ page }) => {
  20 |     await page.goto('http://localhost:3000/auth/login');
  21 |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  22 |     await page.fill('input[type="password"]', 'Customer@001Move');
  23 |     await page.click('button[type="submit"]');
  24 |     
  25 |     await page.goto('http://localhost:3000/customer/rides');
  26 |     
  27 |     await page.fill('input[placeholder*="Where from?"]', 'JFK');
  28 |     await page.click('text=JFK Airport');
  29 |     
  30 |     await page.fill('input[placeholder*="Where to?"]', 'Times');
  31 |     await page.click('text=Times Square');
  32 |     
  33 |     await page.waitForSelector('text=Select a Ride');
  34 |     await page.click('text=OneMove Economy');
  35 |     await page.click('text=Demo Wallet');
  36 |     
  37 |     const confirmButton = page.locator('button', { hasText: 'Confirm Economy' });
  38 |     await expect(confirmButton).toBeEnabled();
  39 |     
  40 |     await confirmButton.click();
  41 |     
  42 |     // Should redirect to a valid details page
  43 |     await expect(page).toHaveURL(/.*\/customer\/rides\/.+/);
  44 |   });
  45 | 
  46 |   // Test 3: Eats Flow
  47 |   test('Customer can add food and checkout', async ({ page }) => {
  48 |     await page.goto('http://localhost:3000/auth/login');
  49 |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  50 |     await page.fill('input[type="password"]', 'Customer@001Move');
  51 |     await page.click('button[type="submit"]');
  52 |     
  53 |     await page.goto('http://localhost:3000/customer/eats');
  54 |     
  55 |     // Click the first restaurant link
  56 |     await page.waitForSelector('a[href^="/customer/eats/"]');
  57 |     await page.click('a[href^="/customer/eats/"]');
  58 |     
  59 |     // Ensure detail page loads properly and we see products or at least the menu client
  60 |     await page.waitForSelector('text=Menu');
  61 |     
  62 |     // Look for an "Add to Cart" button
  63 |     const addButton = page.locator('button', { hasText: /Add \$/ }).first();
  64 |     if (await addButton.isVisible()) {
  65 |       await addButton.click();
  66 |       
  67 |       // Proceed to checkout
  68 |       await page.click('text=Proceed to Checkout');
  69 |       await expect(page).toHaveURL(/.*\/customer\/checkout/);
  70 |       
  71 |       // Select demo wallet and Place Order
  72 |       await page.locator('button', { hasText: 'Demo Wallet' }).click();
  73 |       await page.click('text=Place Order');
  74 |       
  75 |       // Should land on order detail page
  76 |       await expect(page).toHaveURL(/.*\/customer\/orders\/.+/);
  77 |     }
  78 |   });
  79 | 
  80 | });
  81 | 
```