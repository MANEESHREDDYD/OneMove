# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-error-handling.spec.ts >> OneMove Chaos & Error Handling >> Invalid Order ID should gracefully handle missing data
- Location: tests\e2e\onemove-error-handling.spec.ts:4:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=not found').or(locator('text=Invalid order'))
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=not found').or(locator('text=Invalid order'))

```

```yaml
- complementary:
  - link "OneMove":
    - /url: /
  - navigation:
    - link "Dashboard":
      - /url: /customer
    - link "Rides":
      - /url: /customer/rides
    - link "Eats":
      - /url: /customer/eats
    - link "Grocery":
      - /url: /customer/grocery
    - link "Courier":
      - /url: /customer/courier
    - link "Profile":
      - /url: /customer/profile
- main:
  - heading "Your History" [level=1]
  - paragraph: Unified spending and order tracking
  - paragraph: 30-Day Spending
  - paragraph: $1711.61
  - paragraph: Orders
  - paragraph: "39"
  - paragraph: Rides
  - paragraph: "35"
  - paragraph: Avg Value
  - paragraph: $43.89
  - text: Rides
  - paragraph: $1420.71
  - text: Eats
  - paragraph: $0.00
  - text: Grocery
  - paragraph: $290.90
  - text: Courier
  - paragraph: $0.00
  - heading "Active Orders" [level=2]
  - link "ride Service 16/05/2026 • Ordered $172.20 PENDING View details →":
    - /url: /customer/orders/2c2a8968-d342-4c18-ae00-7ba91e3b94a5
    - heading "ride Service" [level=3]
    - paragraph: 16/05/2026 • Ordered
    - text: $172.20 PENDING View details →
  - heading "Grocery Orders" [level=2]
  - link "Organic Basket 25/05/2026 • Completed $55.34 COMPLETED View details →":
    - /url: /customer/orders/891fbcb8-ffe1-4ce6-bcc9-709bd5ff2d88
    - heading "Organic Basket" [level=3]
    - paragraph: 25/05/2026 • Completed
    - text: $55.34 COMPLETED View details →
  - link "Corner Deli & Mart 21/05/2026 • Completed $27.26 COMPLETED View details →":
    - /url: /customer/orders/01da498a-8c6d-4c49-ba9c-56244b0d4f8d
    - heading "Corner Deli & Mart" [level=3]
    - paragraph: 21/05/2026 • Completed
    - text: $27.26 COMPLETED View details →
  - link "FreshDirect Express 19/05/2026 • Completed $168.66 COMPLETED View details →":
    - /url: /customer/orders/2a90ae23-97a5-41b1-8172-218d9d5e8016
    - heading "FreshDirect Express" [level=3]
    - paragraph: 19/05/2026 • Completed
    - text: $168.66 COMPLETED View details →
  - link "City Supermarket 12/05/2026 • Completed $39.64 COMPLETED View details →":
    - /url: /customer/orders/d108942d-7e6c-4f63-8842-fc669b73c4b5
    - heading "City Supermarket" [level=3]
    - paragraph: 12/05/2026 • Completed
    - text: $39.64 COMPLETED View details →
  - heading "Ride History" [level=2]
  - link "ride Service 07/06/2026 • Completed $35.90 COMPLETED View details →":
    - /url: /customer/orders/f1701f88-565b-436a-b77c-5f9fc53f4ac8
    - heading "ride Service" [level=3]
    - paragraph: 07/06/2026 • Completed
    - text: $35.90 COMPLETED View details →
  - link "ride Service 07/06/2026 • Completed $35.28 COMPLETED View details →":
    - /url: /customer/orders/b934ea4e-c29c-4be1-94af-01f2a90d0717
    - heading "ride Service" [level=3]
    - paragraph: 07/06/2026 • Completed
    - text: $35.28 COMPLETED View details →
  - link "ride Service 07/06/2026 • Completed $34.66 COMPLETED View details →":
    - /url: /customer/orders/f0db8d17-6816-47ef-bb6e-c5b3c486be9a
    - heading "ride Service" [level=3]
    - paragraph: 07/06/2026 • Completed
    - text: $34.66 COMPLETED View details →
  - link "ride Service 07/06/2026 • Completed $34.04 COMPLETED View details →":
    - /url: /customer/orders/30d7da94-c86a-4417-ab81-b98a92e3ab23
    - heading "ride Service" [level=3]
    - paragraph: 07/06/2026 • Completed
    - text: $34.04 COMPLETED View details →
  - link "ride Service 07/06/2026 • Completed $33.43 COMPLETED View details →":
    - /url: /customer/orders/3da09b87-0fa7-423b-bd6b-45f0fb70dbcb
    - heading "ride Service" [level=3]
    - paragraph: 07/06/2026 • Completed
    - text: $33.43 COMPLETED View details →
- region "Notifications alt+T"
- alert
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
> 16 |     await expect(page.locator('text=not found').or(page.locator('text=Invalid order'))).toBeVisible();
     |                                                                                         ^ Error: expect(locator).toBeVisible() failed
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
  29 |     await page.locator('button', { hasText: /Add \$/ }).first().click();
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