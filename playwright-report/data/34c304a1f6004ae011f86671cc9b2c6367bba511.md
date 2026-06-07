# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-role-security.spec.ts >> OneMove E2E Role Security >> Partner cannot access admin
- Location: tests\e2e\onemove-role-security.spec.ts:21:7

# Error details

```
Error: page.goto: NS_ERROR_CONNECTION_REFUSED
Call log:
  - navigating to "http://localhost:3000/auth/login", waiting until "load"

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - heading [level=1] [ref=e5]
  - paragraph
  - paragraph
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
  10 |     await page.waitForURL('**/customer**');
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
> 22 |     await page.goto('http://localhost:3000/auth/login');
     |                ^ Error: page.goto: NS_ERROR_CONNECTION_REFUSED
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