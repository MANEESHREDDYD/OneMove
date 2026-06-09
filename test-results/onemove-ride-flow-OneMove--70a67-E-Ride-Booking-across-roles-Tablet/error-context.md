# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-ride-flow.spec.ts >> OneMove Ride Flow >> E2E Ride Booking across roles
- Location: tests\e2e\onemove-ride-flow.spec.ts:21:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Target page, context or browser has been closed
Call log:
  - waiting for locator('button').filter({ hasText: 'Confirm Economy' })

```

# Test source

```ts
  1   | import { test, expect, chromium, Browser, BrowserContext } from '@playwright/test';
  2   | import { assertNoConsoleErrors } from './helpers/assertNoConsoleErrors';
  3   | import { createClient } from '@supabase/supabase-js';
  4   | import dotenv from 'dotenv';
  5   | dotenv.config({ path: '.env.local' });
  6   | 
  7   | test.describe('OneMove Ride Flow', () => {
  8   |   let browser: Browser;
  9   |   let customerCtx: BrowserContext;
  10  |   let partnerCtx: BrowserContext;
  11  |   let adminCtx: BrowserContext;
  12  | 
  13  |   test.beforeAll(async () => {
  14  |     browser = await chromium.launch();
  15  |   });
  16  | 
  17  |   test.afterAll(async () => {
  18  |     await browser.close();
  19  |   });
  20  | 
  21  |   test('E2E Ride Booking across roles', async () => {
  22  |     customerCtx = await browser.newContext();
  23  |     partnerCtx = await browser.newContext();
  24  |     adminCtx = await browser.newContext();
  25  | 
  26  |     const customerPage = await customerCtx.newPage();
  27  |     const partnerPage = await partnerCtx.newPage();
  28  |     const adminPage = await adminCtx.newPage();
  29  | 
  30  |     const checkCustomerErrors = assertNoConsoleErrors(customerPage);
  31  |     const checkPartnerErrors = assertNoConsoleErrors(partnerPage);
  32  |     const checkAdminErrors = assertNoConsoleErrors(adminPage);
  33  | 
  34  |     // Login Roles
  35  |     await Promise.all([
  36  |       (async () => {
  37  |         await customerPage.goto('http://localhost:3000/auth/login');
  38  |         await customerPage.fill('input[type="email"]', 'customer001@onemove.demo');
  39  |         await customerPage.fill('input[type="password"]', 'Customer@001Move');
  40  |         await customerPage.click('button[type="submit"]');
  41  |         await customerPage.waitForURL('**/customer**');
  42  |       })(),
  43  |       (async () => {
  44  |         await partnerPage.goto('http://localhost:3000/auth/login');
  45  |         await partnerPage.fill('input[type="email"]', 'partner001@onemove.demo');
  46  |         await partnerPage.fill('input[type="password"]', 'Partner@001Move');
  47  |         await partnerPage.click('button[type="submit"]');
  48  |         await partnerPage.waitForURL('**/partner**');
  49  |       })(),
  50  |       (async () => {
  51  |         await adminPage.goto('http://localhost:3000/auth/login');
  52  |         await adminPage.fill('input[type="email"]', 'admin@onemove.demo');
  53  |         await adminPage.fill('input[type="password"]', 'Demo@12345');
  54  |         await adminPage.click('button[type="submit"]');
  55  |         await adminPage.waitForURL('**/admin/command-center**');
  56  |       })(),
  57  |     ]);
  58  | 
  59  |     // Reset active jobs so partner can accept a new one
  60  |     const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);
  61  |     await supabase.from('orders').update({ status: 'completed' }).in('status', ['accepted', 'in_transit', 'arrived', 'started', 'picked_up']);
  62  | 
  63  |     // Customer books ride
  64  |     await customerPage.goto('http://localhost:3000/customer/rides');
  65  |     await customerPage.fill('input[placeholder*="Where from?"]', 'JFK');
  66  |     await customerPage.click('text=JFK Airport');
  67  |     await customerPage.fill('input[placeholder*="Where to?"]', 'Times Square');
  68  |     await customerPage.click('text=Times Square');
  69  | 
  70  |     // Select Economy Ride
> 71  |     await customerPage.locator('button', { hasText: 'Confirm Economy' }).click();
      |                                                                          ^ Error: locator.click: Target page, context or browser has been closed
  72  | 
  73  |     // Ensure ride is created and we are redirected to tracking
  74  |     await customerPage.waitForURL(/.*\/customer\/rides\/.*/);
  75  | 
  76  |     await customerPage.waitForURL(/.*\/customer\/rides\/.*/);
  77  |     const rideUrl = customerPage.url();
  78  |     const urlObj = new URL(rideUrl);
  79  |     const rideId = urlObj.pathname.split('/').pop()!;
  80  |     console.log("RIDE ID IS:", rideId);
  81  |     expect(rideId).toBeDefined();
  82  | 
  83  |     // Partner accepts ride
  84  |     await partnerPage.reload();
  85  |     await partnerPage.locator('button', { hasText: 'Accept Job' }).first().click();
  86  |     await partnerPage.locator('button', { hasText: 'Arrived at Pickup' }).click();
  87  |     await partnerPage.locator('button', { hasText: 'Start Ride' }).click();
  88  |     await partnerPage.locator('button', { hasText: 'Complete Ride' }).click();
  89  |     // The button text changes to Updating... so we can't wait for it to be hidden. Wait for the Active Job section to disappear.
  90  |     await partnerPage.locator('text=Active Job').first().waitFor({ state: 'hidden' });
  91  | 
  92  |     // Admin views ride details
  93  |     await adminPage.goto(`http://localhost:3000/admin/orders/${rideId}`);
  94  |     try {
  95  |       await expect(adminPage.getByText('completed', { exact: false }).first()).toBeVisible({ timeout: 5000 });
  96  |     } catch (e) {
  97  |       console.log("Admin Page Content:", await adminPage.content());
  98  |       throw e;
  99  |     }
  100 | 
  101 |     checkCustomerErrors();
  102 |     checkPartnerErrors();
  103 |     checkAdminErrors();
  104 |   });
  105 | });
  106 | 
```