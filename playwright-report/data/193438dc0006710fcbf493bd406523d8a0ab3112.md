# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-performance.spec.ts >> OneMove Performance Budgets >> Customer eats page usable under 2s
- Location: tests\e2e\onemove-performance.spec.ts:5:7

# Error details

```
Error: page.goto: Navigation to "http://localhost:3000/customer/eats" is interrupted by another navigation to "http://localhost:3000/customer"
Call log:
  - navigating to "http://localhost:3000/customer/eats", waiting until "load"

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - main [ref=e3]:
      - generic [ref=e5]:
        - generic [ref=e6]:
          - generic [ref=e8]:
            - heading "Good Morning" [level=1] [ref=e9]
            - paragraph [ref=e10]: Where to next?
          - button "Sign Out" [ref=e11]:
            - img
            - text: Sign Out
        - generic [ref=e12]:
          - generic [ref=e13]:
            - heading "Active Orders" [level=2] [ref=e14]
            - link "View all" [ref=e15]:
              - /url: /customer/orders
          - link "ride • pending 8812 Maymie Lodge, New York, NY" [ref=e17]:
            - /url: /customer/orders/2c2a8968-d342-4c18-ae00-7ba91e3b94a5
            - generic [ref=e18] [cursor=pointer]:
              - img [ref=e20]
              - generic [ref=e24]:
                - heading "ride • pending" [level=3] [ref=e25]
                - generic [ref=e26]:
                  - img [ref=e27]
                  - generic [ref=e30]: 8812 Maymie Lodge, New York, NY
        - generic [ref=e31]:
          - heading "Services" [level=2] [ref=e32]
          - generic [ref=e33]:
            - link "Rides Get there fast" [ref=e34]:
              - /url: /customer/rides
              - generic [ref=e35] [cursor=pointer]:
                - img [ref=e38]
                - generic [ref=e42]:
                  - heading "Rides" [level=3] [ref=e43]
                  - paragraph [ref=e44]: Get there fast
            - link "Food Cravings delivered" [ref=e45]:
              - /url: /customer/eats
              - generic [ref=e46] [cursor=pointer]:
                - img [ref=e49]
                - generic [ref=e52]:
                  - heading "Food" [level=3] [ref=e53]
                  - paragraph [ref=e54]: Cravings delivered
            - link "Grocery Fresh & fast" [ref=e55]:
              - /url: /customer/grocery
              - generic [ref=e56] [cursor=pointer]:
                - img [ref=e59]
                - generic [ref=e65]:
                  - heading "Grocery" [level=3] [ref=e66]
                  - paragraph [ref=e67]: Fresh & fast
            - link "Courier Send packages" [ref=e68]:
              - /url: /customer/orders
              - generic [ref=e69] [cursor=pointer]:
                - img [ref=e72]
                - generic [ref=e76]:
                  - heading "Courier" [level=3] [ref=e77]
                  - paragraph [ref=e78]: Send packages
        - generic [ref=e81]:
          - heading "Try OneMove Prime" [level=3] [ref=e82]
          - paragraph [ref=e83]: Get $0 delivery fees on eligible food and grocery orders, plus 5% off rides.
          - button "Start Free Trial" [ref=e84]
        - button [ref=e86]:
          - img [ref=e87]
    - navigation [ref=e89]:
      - generic [ref=e90]:
        - link "Dashboard" [ref=e91]:
          - /url: /customer
          - img [ref=e92]
          - generic [ref=e97]: Dashboard
        - link "Rides" [ref=e98]:
          - /url: /customer/rides
          - img [ref=e99]
          - generic [ref=e103]: Rides
        - link "Eats" [ref=e104]:
          - /url: /customer/eats
          - img [ref=e105]
          - generic [ref=e108]: Eats
        - link "Grocery" [ref=e109]:
          - /url: /customer/grocery
          - img [ref=e110]
          - generic [ref=e113]: Grocery
        - link "Courier" [ref=e114]:
          - /url: /customer/courier
          - img [ref=e115]
          - generic [ref=e119]: Courier
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e125] [cursor=pointer]:
    - img [ref=e126]
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
> 14 |     await page.goto('http://localhost:3000/customer/eats');
     |                ^ Error: page.goto: Navigation to "http://localhost:3000/customer/eats" is interrupted by another navigation to "http://localhost:3000/customer"
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
  32 |     await page.waitForSelector('text=Active Orders');
  33 |     const loadTime = Date.now() - startTime;
  34 |     
  35 |     expect(loadTime).toBeLessThan(4000); // 4 seconds allowance for admin dashboard
  36 |   });
  37 | });
  38 | 
```