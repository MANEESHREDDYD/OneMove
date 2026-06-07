# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-performance.spec.ts >> OneMove Performance Budgets >> Admin command center loads efficiently
- Location: tests\e2e\onemove-performance.spec.ts:23:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.waitForSelector: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('text=Active Orders') to be visible

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
          - paragraph [ref=e36]: Login as Partner / Driver
        - button "Login as Merchant" [ref=e37]:
          - img [ref=e38]
          - paragraph [ref=e42]: Login as Merchant
        - button "Login as Admin" [ref=e43]:
          - img [ref=e44]
          - paragraph [ref=e46]: Login as Admin
  - region "Notifications alt+T"
  - alert [ref=e47]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('OneMove Performance Budgets', () => {
  4  |   // Test navigation performance
  5  |   test('Customer eats page usable under 2s', async ({ page }) => {
  6  |     await page.goto('http://localhost:3000/auth/login');
  7  |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  8  |     await page.fill('input[type="password"]', 'Customer@001Move');
  9  |     await page.click('button[type="submit"]');
  10 |     
  11 |     await page.waitForURL('**/customer**');
  12 |     
  13 |     const startTime = Date.now();
  14 |     await page.goto('http://localhost:3000/customer/eats');
  15 |     // Wait for restaurants to populate
  16 |     await page.waitForSelector('a[href^="/customer/eats/"]');
  17 |     const loadTime = Date.now() - startTime;
  18 |     
  19 |     // Performance budget assertion
  20 |     expect(loadTime).toBeLessThan(3000); // 3 seconds allowance for local dev
  21 |   });
  22 | 
  23 |   test('Admin command center loads efficiently', async ({ page }) => {
  24 |     await page.goto('http://localhost:3000/auth/login');
  25 |     await page.fill('input[type="email"]', 'admin001@onemove.demo'); // Assume admin credential structure
  26 |     await page.fill('input[type="password"]', 'Demo@12345');
  27 |     await page.click('button[type="submit"]');
  28 |     
  29 |     const startTime = Date.now();
  30 |     await page.goto('http://localhost:3000/admin/command-center');
  31 |     // Ensure dashboard renders
> 32 |     await page.waitForSelector('text=Active Orders');
     |                ^ Error: page.waitForSelector: Test timeout of 30000ms exceeded.
  33 |     const loadTime = Date.now() - startTime;
  34 |     
  35 |     expect(loadTime).toBeLessThan(4000); // 4 seconds allowance for admin dashboard
  36 |   });
  37 | });
  38 | 
```