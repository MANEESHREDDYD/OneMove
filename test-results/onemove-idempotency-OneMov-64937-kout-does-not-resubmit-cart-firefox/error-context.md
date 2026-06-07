# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-idempotency.spec.ts >> OneMove Idempotency >> Browser Back button after successful checkout does not resubmit cart
- Location: tests\e2e\onemove-idempotency.spec.ts:5:7

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
          - generic [ref=e20]: Rides
        - link "Eats" [ref=e21] [cursor=pointer]:
          - /url: /customer/eats
          - img [ref=e22]
          - generic [ref=e26]: Eats
        - link "Grocery" [ref=e27] [cursor=pointer]:
          - /url: /customer/grocery
          - img [ref=e28]
          - generic [ref=e32]: Grocery
        - link "Courier" [ref=e33] [cursor=pointer]:
          - /url: /customer/courier
          - img [ref=e34]
          - generic [ref=e39]: Courier
        - link "Profile" [ref=e40] [cursor=pointer]:
          - /url: /customer/profile
          - img [ref=e41]
          - generic [ref=e44]: Profile
    - main [ref=e45]:
      - generic [ref=e47]:
        - generic [ref=e49]:
          - heading "Pizza Napoli" [level=1] [ref=e50]
          - paragraph [ref=e51]: Select items to add to your order
        - generic [ref=e52]:
          - generic [ref=e53]:
            - generic [ref=e54]:
              - heading "Spicy Tuna Roll" [level=3] [ref=e55]
              - paragraph [ref=e56]: Japanese specialty
              - paragraph [ref=e57]: $6.89
            - button [ref=e59]:
              - img [ref=e60]
          - generic [ref=e63]:
            - generic [ref=e64]:
              - heading "Dragon Roll" [level=3] [ref=e65]
              - paragraph [ref=e66]: Japanese specialty
              - paragraph [ref=e67]: $24.48
            - button [ref=e69]:
              - img [ref=e70]
          - generic [ref=e73]:
            - generic [ref=e74]:
              - heading "Miso Soup" [level=3] [ref=e75]
              - paragraph [ref=e76]: Japanese specialty
              - paragraph [ref=e77]: $12.02
            - button [ref=e79]:
              - img [ref=e80]
          - generic [ref=e83]:
            - generic [ref=e84]:
              - heading "Edamame" [level=3] [ref=e85]
              - paragraph [ref=e86]: Japanese specialty
              - paragraph [ref=e87]: $18.64
            - button [ref=e89]:
              - img [ref=e90]
          - generic [ref=e93]:
            - generic [ref=e94]:
              - heading "Teriyaki Chicken" [level=3] [ref=e95]
              - paragraph [ref=e96]: Japanese specialty
              - paragraph [ref=e97]: $26.52
            - button [ref=e99]:
              - img [ref=e100]
          - generic [ref=e103]:
            - generic [ref=e104]:
              - heading "Ramen Tonkotsu" [level=3] [ref=e105]
              - paragraph [ref=e106]: Japanese specialty
              - paragraph [ref=e107]: $24.42
            - button [ref=e109]:
              - img [ref=e110]
          - generic [ref=e113]:
            - generic [ref=e114]:
              - heading "Tempura Shrimp" [level=3] [ref=e115]
              - paragraph [ref=e116]: Japanese specialty
              - paragraph [ref=e117]: $13.79
            - button [ref=e119]:
              - img [ref=e120]
          - generic [ref=e123]:
            - generic [ref=e124]:
              - heading "Salmon Sashimi" [level=3] [ref=e125]
              - paragraph [ref=e126]: Japanese specialty
              - paragraph [ref=e127]: $16.89
            - button [ref=e129]:
              - img [ref=e130]
          - generic [ref=e133]:
            - generic [ref=e134]:
              - heading "Gyoza (6pc)" [level=3] [ref=e135]
              - paragraph [ref=e136]: Japanese specialty
              - paragraph [ref=e137]: $7.46
            - button [ref=e139]:
              - img [ref=e140]
          - generic [ref=e143]:
            - generic [ref=e144]:
              - heading "Matcha Ice Cream" [level=3] [ref=e145]
              - paragraph [ref=e146]: Japanese specialty
              - paragraph [ref=e147]: $23.45
            - button [ref=e149]:
              - img [ref=e150]
  - region "Notifications alt+T"
  - alert [ref=e153]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | import { assertNoConsoleErrors } from './helpers/assertNoConsoleErrors';
  3  | 
  4  | test.describe('OneMove Idempotency', () => {
  5  |   test('Browser Back button after successful checkout does not resubmit cart', async ({ page }) => {
  6  |     const checkErrors = assertNoConsoleErrors(page);
  7  |     
  8  |     await page.goto('http://localhost:3000/auth/login');
  9  |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  10 |     await page.fill('input[type="password"]', 'Customer@001Move');
  11 |     await page.click('button[type="submit"]');
  12 |     
  13 |     await page.waitForURL('**/customer**');
  14 |     
  15 |     // Add item and checkout
  16 |     await page.goto('http://localhost:3000/customer/eats');
  17 |     await page.click('a[href^="/customer/eats/"]');
> 18 |     await page.locator('button', { hasText: /Add \$/ }).first().click();
     |                                                                 ^ Error: locator.click: Test timeout of 30000ms exceeded.
  19 |     await page.click('text=View Cart & Checkout');
  20 |     
  21 |     await page.waitForURL(/.*\/customer\/checkout/);
  22 |     await page.locator('button', { hasText: 'Demo Wallet' }).click();
  23 |     await page.locator('button', { hasText: 'Place Order' }).click();
  24 |     
  25 |     // Land on order tracking
  26 |     await page.waitForURL(/.*\/customer\/orders\/.*/);
  27 |     
  28 |     // Hit browser back
  29 |     await page.goBack();
  30 |     
  31 |     // Attempting to resubmit the same cart should either show it's empty, or the idempotency key in the action should reject it.
  32 |     // Assuming UI handles empty cart by disabling Place Order.
  33 |     const placeOrderBtn = page.locator('button:has-text("Place Order")');
  34 |     if (await placeOrderBtn.isVisible()) {
  35 |       await expect(placeOrderBtn).toBeDisabled();
  36 |     }
  37 |     
  38 |     checkErrors();
  39 |   });
  40 | });
  41 | 
```