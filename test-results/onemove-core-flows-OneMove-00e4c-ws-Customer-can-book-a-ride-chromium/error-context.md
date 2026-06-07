# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-core-flows.spec.ts >> OneMove Core Marketplace E2E Flows >> Customer can book a ride
- Location: tests\e2e\onemove-core-flows.spec.ts:19:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.fill: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('input[placeholder*="Where from?"]')

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
  - button "Open Next.js Dev Tools" [ref=e51] [cursor=pointer]:
    - generic [ref=e54]:
      - text: Compiling
      - generic [ref=e55]:
        - generic [ref=e56]: .
        - generic [ref=e57]: .
        - generic [ref=e58]: .
  - alert [ref=e59]
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
  11 |     await expect(page).toHaveURL(/.*\/customer/);
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
> 27 |     await page.fill('input[placeholder*="Where from?"]', 'JFK');
     |                ^ Error: page.fill: Test timeout of 30000ms exceeded.
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