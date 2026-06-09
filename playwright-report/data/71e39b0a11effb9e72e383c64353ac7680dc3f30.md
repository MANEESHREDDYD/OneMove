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
      - link "OneMove" [ref=e5]:
        - /url: /
      - navigation [ref=e6]:
        - link "Dashboard" [ref=e7]:
          - /url: /customer
          - img [ref=e8]
          - generic [ref=e13]: Dashboard
        - link "Rides" [ref=e14]:
          - /url: /customer/rides
          - img [ref=e15]
          - generic [ref=e19]: Rides
        - link "Eats" [ref=e20]:
          - /url: /customer/eats
          - img [ref=e21]
          - generic [ref=e24]: Eats
        - link "Grocery" [ref=e25]:
          - /url: /customer/grocery
          - img [ref=e26]
          - generic [ref=e29]: Grocery
        - link "Courier" [ref=e30]:
          - /url: /customer/courier
          - img [ref=e31]
          - generic [ref=e35]: Courier
        - link "Support" [ref=e36]:
          - /url: /customer/support
          - img [ref=e37]
          - generic [ref=e44]: Support
        - link "Profile" [ref=e45]:
          - /url: /customer/profile
          - img [ref=e46]
          - generic [ref=e49]: Profile
    - main [ref=e50]:
      - generic [ref=e52]:
        - generic [ref=e54]:
          - heading "Pizza Napoli" [level=1] [ref=e55]
          - paragraph [ref=e56]: Select items to add to your order
        - generic [ref=e57]:
          - generic [ref=e58]:
            - generic [ref=e59]:
              - heading "Spicy Tuna Roll" [level=3] [ref=e60]
              - paragraph [ref=e61]: Japanese specialty
              - paragraph [ref=e62]: $6.89
            - button [ref=e64]:
              - img [ref=e65]
          - generic [ref=e66]:
            - generic [ref=e67]:
              - heading "Dragon Roll" [level=3] [ref=e68]
              - paragraph [ref=e69]: Japanese specialty
              - paragraph [ref=e70]: $24.48
            - button [ref=e72]:
              - img [ref=e73]
          - generic [ref=e74]:
            - generic [ref=e75]:
              - heading "Miso Soup" [level=3] [ref=e76]
              - paragraph [ref=e77]: Japanese specialty
              - paragraph [ref=e78]: $12.02
            - button [ref=e80]:
              - img [ref=e81]
          - generic [ref=e82]:
            - generic [ref=e83]:
              - heading "Edamame" [level=3] [ref=e84]
              - paragraph [ref=e85]: Japanese specialty
              - paragraph [ref=e86]: $18.64
            - button [ref=e88]:
              - img [ref=e89]
          - generic [ref=e90]:
            - generic [ref=e91]:
              - heading "Teriyaki Chicken" [level=3] [ref=e92]
              - paragraph [ref=e93]: Japanese specialty
              - paragraph [ref=e94]: $26.52
            - button [ref=e96]:
              - img [ref=e97]
          - generic [ref=e98]:
            - generic [ref=e99]:
              - heading "Ramen Tonkotsu" [level=3] [ref=e100]
              - paragraph [ref=e101]: Japanese specialty
              - paragraph [ref=e102]: $24.42
            - button [ref=e104]:
              - img [ref=e105]
          - generic [ref=e106]:
            - generic [ref=e107]:
              - heading "Tempura Shrimp" [level=3] [ref=e108]
              - paragraph [ref=e109]: Japanese specialty
              - paragraph [ref=e110]: $13.79
            - button [ref=e112]:
              - img [ref=e113]
          - generic [ref=e114]:
            - generic [ref=e115]:
              - heading "Salmon Sashimi" [level=3] [ref=e116]
              - paragraph [ref=e117]: Japanese specialty
              - paragraph [ref=e118]: $16.89
            - button [ref=e120]:
              - img [ref=e121]
          - generic [ref=e122]:
            - generic [ref=e123]:
              - heading "Gyoza (6pc)" [level=3] [ref=e124]
              - paragraph [ref=e125]: Japanese specialty
              - paragraph [ref=e126]: $7.46
            - button [ref=e128]:
              - img [ref=e129]
          - generic [ref=e130]:
            - generic [ref=e131]:
              - heading "Matcha Ice Cream" [level=3] [ref=e132]
              - paragraph [ref=e133]: Japanese specialty
              - paragraph [ref=e134]: $23.45
            - button [ref=e136]:
              - img [ref=e137]
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e143] [cursor=pointer]:
    - img [ref=e144]
  - alert [ref=e149]
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