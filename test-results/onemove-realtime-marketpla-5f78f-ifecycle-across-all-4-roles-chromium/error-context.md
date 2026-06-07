# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-realtime-marketplace.spec.ts >> OneMove Realtime Marketplace Flow >> E2E Order Lifecycle across all 4 roles
- Location: tests\e2e\onemove-realtime-marketplace.spec.ts:19:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Target page, context or browser has been closed
Call log:
  - waiting for locator('button').filter({ hasText: /Add \$/ }).first()

```

# Test source

```ts
  1   | import { test, expect, chromium, Browser, BrowserContext } from '@playwright/test';
  2   | import { assertNoConsoleErrors } from './helpers/assertNoConsoleErrors';
  3   | 
  4   | test.describe('OneMove Realtime Marketplace Flow', () => {
  5   |   let browser: Browser;
  6   |   let customerCtx: BrowserContext;
  7   |   let merchantCtx: BrowserContext;
  8   |   let partnerCtx: BrowserContext;
  9   |   let adminCtx: BrowserContext;
  10  | 
  11  |   test.beforeAll(async () => {
  12  |     browser = await chromium.launch();
  13  |   });
  14  | 
  15  |   test.afterAll(async () => {
  16  |     await browser.close();
  17  |   });
  18  | 
  19  |   test('E2E Order Lifecycle across all 4 roles', async () => {
  20  |     // 1. Setup contexts
  21  |     customerCtx = await browser.newContext();
  22  |     merchantCtx = await browser.newContext();
  23  |     partnerCtx = await browser.newContext();
  24  |     adminCtx = await browser.newContext();
  25  | 
  26  |     const customerPage = await customerCtx.newPage();
  27  |     const merchantPage = await merchantCtx.newPage();
  28  |     const partnerPage = await partnerCtx.newPage();
  29  |     const adminPage = await adminCtx.newPage();
  30  |     
  31  |     const checkCustomerErrors = assertNoConsoleErrors(customerPage);
  32  |     const checkMerchantErrors = assertNoConsoleErrors(merchantPage);
  33  |     const checkPartnerErrors = assertNoConsoleErrors(partnerPage);
  34  |     const checkAdminErrors = assertNoConsoleErrors(adminPage);
  35  | 
  36  |     // 2. Login all roles simultaneously
  37  |     await Promise.all([
  38  |       (async () => {
  39  |         await customerPage.goto('http://localhost:3000/auth/login');
  40  |         await customerPage.fill('input[type="email"]', 'customer001@onemove.demo');
  41  |         await customerPage.fill('input[type="password"]', 'Customer@001Move');
  42  |         await customerPage.click('button[type="submit"]');
  43  |         await customerPage.waitForURL('**/customer**');
  44  |       })(),
  45  |       (async () => {
  46  |         await merchantPage.goto('http://localhost:3000/auth/login');
  47  |         await merchantPage.fill('input[type="email"]', 'merchant001@onemove.demo');
  48  |         await merchantPage.fill('input[type="password"]', 'Merchant@001Move');
  49  |         await merchantPage.click('button[type="submit"]');
  50  |         await merchantPage.waitForURL('**/merchant**');
  51  |       })(),
  52  |       (async () => {
  53  |         await partnerPage.goto('http://localhost:3000/auth/login');
  54  |         await partnerPage.fill('input[type="email"]', 'partner001@onemove.demo');
  55  |         await partnerPage.fill('input[type="password"]', 'Partner@001Move');
  56  |         await partnerPage.click('button[type="submit"]');
  57  |         await partnerPage.waitForURL('**/partner**');
  58  |       })(),
  59  |       (async () => {
  60  |         await adminPage.goto('http://localhost:3000/auth/login');
  61  |         await adminPage.fill('input[type="email"]', 'admin@onemove.demo');
  62  |         await adminPage.fill('input[type="password"]', 'Demo@12345');
  63  |         await adminPage.click('button[type="submit"]');
  64  |         await adminPage.waitForURL('**/admin/command-center**');
  65  |       })(),
  66  |     ]);
  67  | 
  68  |     // 3. Customer places an order
  69  |     await customerPage.goto('http://localhost:3000/customer/eats');
  70  |     await customerPage.waitForSelector('a[href^="/customer/eats/"]');
  71  |     await customerPage.click('a[href^="/customer/eats/"]');
> 72  |     await customerPage.locator('button', { hasText: /Add \$/ }).first().click();
      |                                                                         ^ Error: locator.click: Target page, context or browser has been closed
  73  |     await customerPage.click('text=View Cart & Checkout');
  74  |     await expect(customerPage).toHaveURL(/.*\/customer\/checkout/);
  75  |     await customerPage.locator('button', { hasText: 'Demo Wallet' }).click();
  76  |     await customerPage.click('text=Place Order');
  77  |     
  78  |     // Extract Order ID from tracking page
  79  |     await customerPage.waitForURL(/.*\/customer\/orders\/.*/);
  80  |     const orderUrl = customerPage.url();
  81  |     const orderId = orderUrl.split('/').pop()!;
  82  |     expect(orderId).toBeDefined();
  83  | 
  84  |     // 4. Merchant accepts order (assuming manual refresh if realtime is missing)
  85  |     await merchantPage.reload(); // Fallback for lack of WebSockets
  86  |     const acceptBtn = merchantPage.locator(`button[data-order-id="${orderId}"]`, { hasText: 'Accept' });
  87  |     if (await acceptBtn.isVisible()) {
  88  |       await acceptBtn.click();
  89  |       await merchantPage.locator(`button[data-order-id="${orderId}"]`, { hasText: 'Ready' }).click();
  90  |     } else {
  91  |       // It might be in a different tab or not visible yet
  92  |       // Click first Accept button found for demo robustness
  93  |       await merchantPage.locator('button', { hasText: 'Accept' }).first().click();
  94  |       await merchantPage.locator('button', { hasText: 'Ready' }).first().click();
  95  |     }
  96  | 
  97  |     // 5. Partner accepts job
  98  |     await partnerPage.reload();
  99  |     await partnerPage.locator('button', { hasText: 'Accept Job' }).first().click();
  100 |     await expect(partnerPage.locator('button', { hasText: 'Mark Picked Up' })).toBeVisible();
  101 |     await partnerPage.locator('button', { hasText: 'Mark Picked Up' }).click();
  102 |     await partnerPage.locator('button', { hasText: 'Mark Delivered' }).click();
  103 | 
  104 |     // 6. Customer sees tracking updated
  105 |     await customerPage.reload();
  106 |     await expect(customerPage.locator('text=delivered')).toBeVisible();
  107 | 
  108 |     // 7. Admin sees order in command center
  109 |     await adminPage.reload();
  110 |     await adminPage.goto(`http://localhost:3000/admin/orders/${orderId}`);
  111 |     await expect(adminPage.locator('text=delivered')).toBeVisible();
  112 |     
  113 |     // 8. Assert no console errors
  114 |     checkCustomerErrors();
  115 |     checkMerchantErrors();
  116 |     checkPartnerErrors();
  117 |     checkAdminErrors();
  118 |   });
  119 | });
  120 | 
```