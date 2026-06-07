# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-role-security.spec.ts >> OneMove E2E Role Security >> Customer cannot access admin or merchant routes
- Location: tests\e2e\onemove-role-security.spec.ts:4:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: page.waitForURL: Test timeout of 30000ms exceeded.
=========================== logs ===========================
waiting for navigation to "**/customer**" until "load"
============================================================
```

# Page snapshot

```yaml
- generic [ref=e1]:
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
            - text: customer001@onemove.demo
        - generic [ref=e12]:
          - generic [ref=e13]: Password
          - textbox "Password" [ref=e14]: Customer@001Move
        - button "Sign In" [active] [ref=e15]
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
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('OneMove E2E Role Security', () => {
  4  |   test('Customer cannot access admin or merchant routes', async ({ page }) => {
  5  |     await page.goto('http://localhost:3000/auth/login');
  6  |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  7  |     await page.fill('input[type="password"]', 'Customer@001Move');
  8  |     await page.click('button[type="submit"]');
  9  |     
> 10 |     await page.waitForURL('**/customer**');
     |                ^ Error: page.waitForURL: Test timeout of 30000ms exceeded.
  11 |     
  12 |     // Attempt Admin Access
  13 |     await page.goto('http://localhost:3000/admin/command-center');
  14 |     await expect(page).toHaveURL(/.*\/customer|.*\/auth\/login/); // Should bounce
  15 |     
  16 |     // Attempt Merchant Access
  17 |     await page.goto('http://localhost:3000/merchant');
  18 |     await expect(page).toHaveURL(/.*\/customer|.*\/auth\/login/); // Should bounce
  19 |   });
  20 |   
  21 |   test('Partner cannot access admin', async ({ page }) => {
  22 |     await page.goto('http://localhost:3000/auth/login');
  23 |     await page.fill('input[type="email"]', 'partner001@onemove.demo');
  24 |     await page.fill('input[type="password"]', 'Partner@001Move');
  25 |     await page.click('button[type="submit"]');
  26 |     
  27 |     await page.waitForURL('**/partner**');
  28 |     
  29 |     // Attempt Admin Access
  30 |     await page.goto('http://localhost:3000/admin/command-center');
  31 |     await expect(page).toHaveURL(/.*\/partner|.*\/auth\/login/); // Should bounce
  32 |   });
  33 | });
  34 | 
```