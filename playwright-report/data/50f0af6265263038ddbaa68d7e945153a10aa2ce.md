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