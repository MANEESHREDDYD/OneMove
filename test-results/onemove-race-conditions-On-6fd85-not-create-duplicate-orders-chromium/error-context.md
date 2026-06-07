# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-race-conditions.spec.ts >> OneMove Race Conditions & Idempotency >> Double-clicking Place Order should not create duplicate orders
- Location: tests\e2e\onemove-race-conditions.spec.ts:4:7

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
  - generic [ref=e2]:
    - complementary [ref=e3]:
      - link "OneMove" [ref=e5] [cursor=pointer]:
        - /url: /
      - navigation [ref=e6]:
        - link "Dashboard" [ref=e7] [cursor=pointer]:
          - /url: /customer
          - img [ref=e8]
          - generic [ref=e13]: Dashboard
        - link "Rides" [ref=e14] [cursor=pointer]:
          - /url: /customer/rides
          - img [ref=e15]
          - generic [ref=e19]: Rides
        - link "Eats" [ref=e20] [cursor=pointer]:
          - /url: /customer/eats
          - img [ref=e21]
          - generic [ref=e24]: Eats
        - link "Grocery" [ref=e25] [cursor=pointer]:
          - /url: /customer/grocery
          - img [ref=e26]
          - generic [ref=e29]: Grocery
        - link "Courier" [ref=e30] [cursor=pointer]:
          - /url: /customer/courier
          - img [ref=e31]
          - generic [ref=e35]: Courier
        - link "Profile" [ref=e36] [cursor=pointer]:
          - /url: /customer/profile
          - img [ref=e37]
          - generic [ref=e40]: Profile
    - main [ref=e41]:
      - generic [ref=e43]:
        - generic [ref=e45]:
          - heading "Pizza Napoli" [level=1] [ref=e46]
          - paragraph [ref=e47]: Select items to add to your order
        - generic [ref=e48]:
          - generic [ref=e49]:
            - generic [ref=e50]:
              - heading "Spicy Tuna Roll" [level=3] [ref=e51]
              - paragraph [ref=e52]: Japanese specialty
              - paragraph [ref=e53]: $6.89
            - button [ref=e55]:
              - img [ref=e56]
          - generic [ref=e57]:
            - generic [ref=e58]:
              - heading "Dragon Roll" [level=3] [ref=e59]
              - paragraph [ref=e60]: Japanese specialty
              - paragraph [ref=e61]: $24.48
            - button [ref=e63]:
              - img [ref=e64]
          - generic [ref=e65]:
            - generic [ref=e66]:
              - heading "Miso Soup" [level=3] [ref=e67]
              - paragraph [ref=e68]: Japanese specialty
              - paragraph [ref=e69]: $12.02
            - button [ref=e71]:
              - img [ref=e72]
          - generic [ref=e73]:
            - generic [ref=e74]:
              - heading "Edamame" [level=3] [ref=e75]
              - paragraph [ref=e76]: Japanese specialty
              - paragraph [ref=e77]: $18.64
            - button [ref=e79]:
              - img [ref=e80]
          - generic [ref=e81]:
            - generic [ref=e82]:
              - heading "Teriyaki Chicken" [level=3] [ref=e83]
              - paragraph [ref=e84]: Japanese specialty
              - paragraph [ref=e85]: $26.52
            - button [ref=e87]:
              - img [ref=e88]
          - generic [ref=e89]:
            - generic [ref=e90]:
              - heading "Ramen Tonkotsu" [level=3] [ref=e91]
              - paragraph [ref=e92]: Japanese specialty
              - paragraph [ref=e93]: $24.42
            - button [ref=e95]:
              - img [ref=e96]
          - generic [ref=e97]:
            - generic [ref=e98]:
              - heading "Tempura Shrimp" [level=3] [ref=e99]
              - paragraph [ref=e100]: Japanese specialty
              - paragraph [ref=e101]: $13.79
            - button [ref=e103]:
              - img [ref=e104]
          - generic [ref=e105]:
            - generic [ref=e106]:
              - heading "Salmon Sashimi" [level=3] [ref=e107]
              - paragraph [ref=e108]: Japanese specialty
              - paragraph [ref=e109]: $16.89
            - button [ref=e111]:
              - img [ref=e112]
          - generic [ref=e113]:
            - generic [ref=e114]:
              - heading "Gyoza (6pc)" [level=3] [ref=e115]
              - paragraph [ref=e116]: Japanese specialty
              - paragraph [ref=e117]: $7.46
            - button [ref=e119]:
              - img [ref=e120]
          - generic [ref=e121]:
            - generic [ref=e122]:
              - heading "Matcha Ice Cream" [level=3] [ref=e123]
              - paragraph [ref=e124]: Japanese specialty
              - paragraph [ref=e125]: $23.45
            - button [ref=e127]:
              - img [ref=e128]
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e134] [cursor=pointer]:
    - generic [ref=e137]:
      - text: Compiling
      - generic [ref=e138]:
        - generic [ref=e139]: .
        - generic [ref=e140]: .
        - generic [ref=e141]: .
  - alert [ref=e142]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('OneMove Race Conditions & Idempotency', () => {
  4  |   test('Double-clicking Place Order should not create duplicate orders', async ({ page }) => {
  5  |     await page.goto('http://localhost:3000/auth/login');
  6  |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  7  |     await page.fill('input[type="password"]', 'Customer@001Move');
  8  |     await page.click('button[type="submit"]');
  9  |     
  10 |     await page.waitForURL('**/customer**');
  11 |     
  12 |     // Add item and go to checkout
  13 |     await page.goto('http://localhost:3000/customer/eats');
  14 |     await page.click('a[href^="/customer/eats/"]');
> 15 |     await page.locator('button', { hasText: /Add \$/ }).first().click();
     |                                                                 ^ Error: locator.click: Test timeout of 30000ms exceeded.
  16 |     await page.click('text=View Cart & Checkout');
  17 |     
  18 |     await page.waitForURL(/.*\/customer\/checkout/);
  19 |     await page.locator('button', { hasText: 'Demo Wallet' }).click();
  20 |     
  21 |     // SPAM CLICK "Place Order"
  22 |     const placeOrderBtn = page.locator('button', { hasText: 'Place Order' });
  23 |     await Promise.all([
  24 |       placeOrderBtn.click({ force: true }),
  25 |       placeOrderBtn.click({ force: true }),
  26 |       placeOrderBtn.click({ force: true }),
  27 |     ]);
  28 |     
  29 |     // Should navigate away to exactly one order tracking page
  30 |     await page.waitForURL(/.*\/customer\/orders\/.*/);
  31 |     
  32 |     // We would need to hit the DB or Admin panel to strictly verify no dupes were created.
  33 |     // For now, ensuring it doesn't crash or hang, and successfully routes.
  34 |     // We can navigate to order history to count recent orders.
  35 |     await page.goto('http://localhost:3000/customer/orders');
  36 |     // Assuming UI shows a list, we just make sure there isn't a massive blast of identical active orders
  37 |     // Real strict verification is done by checking the DB via an API or Admin view, 
  38 |     // which our backend contracts test handles more rigorously.
  39 |   });
  40 | });
  41 | 
```