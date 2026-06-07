# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-session-hardening.spec.ts >> OneMove Session Hardening & Stale State >> Cross-tab sign-out logs out all tabs and blocks back-button caching
- Location: tests\e2e\onemove-session-hardening.spec.ts:4:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text="Sign Out"')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text="Sign Out"')

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
  - heading "OneMove Eats" [level=1]
  - paragraph: Craving something? We'll bring it.
  - heading "Trending Near You" [level=2]
  - link "restaurant Cuisine Pizza Napoli 5 25-40 min":
    - /url: /customer/eats/dc02a591-10b8-4cbc-8f73-55f63c001f41
    - paragraph: restaurant Cuisine
    - heading "Pizza Napoli" [level=3]
    - text: 5 25-40 min
  - link "restaurant Cuisine Green Bowl Co. 4.9 25-40 min":
    - /url: /customer/eats/c73f22fa-e851-4d30-9a99-0fd26528cea9
    - paragraph: restaurant Cuisine
    - heading "Green Bowl Co." [level=3]
    - text: 4.9 25-40 min
  - link "restaurant Cuisine Little Italy Deli 4.9 25-40 min":
    - /url: /customer/eats/14f25878-ea6e-451d-b93d-340d3659b3d5
    - paragraph: restaurant Cuisine
    - heading "Little Italy Deli" [level=3]
    - text: 4.9 25-40 min
  - link "restaurant Cuisine Fresh Kitchen 4.9 25-40 min":
    - /url: /customer/eats/e947a1d0-1e44-4f89-b5b6-f16ddfad545c
    - paragraph: restaurant Cuisine
    - heading "Fresh Kitchen" [level=3]
    - text: 4.9 25-40 min
  - heading "All Restaurants" [level=2]
  - link "P Pizza Napoli Japanese cuisine • Free delivery over $25 5 20-35 min":
    - /url: /customer/eats/dc02a591-10b8-4cbc-8f73-55f63c001f41
    - text: P
    - heading "Pizza Napoli" [level=3]
    - paragraph: Japanese cuisine • Free delivery over $25
    - text: 5 20-35 min
  - link "G Green Bowl Co. Mexican cuisine • Free delivery over $25 4.9 20-35 min":
    - /url: /customer/eats/c73f22fa-e851-4d30-9a99-0fd26528cea9
    - text: G
    - heading "Green Bowl Co." [level=3]
    - paragraph: Mexican cuisine • Free delivery over $25
    - text: 4.9 20-35 min
  - link "L Little Italy Deli Chinese cuisine • Free delivery over $25 4.9 20-35 min":
    - /url: /customer/eats/14f25878-ea6e-451d-b93d-340d3659b3d5
    - text: L
    - heading "Little Italy Deli" [level=3]
    - paragraph: Chinese cuisine • Free delivery over $25
    - text: 4.9 20-35 min
  - link "F Fresh Kitchen Chinese cuisine • Free delivery over $25 4.9 20-35 min":
    - /url: /customer/eats/e947a1d0-1e44-4f89-b5b6-f16ddfad545c
    - text: F
    - heading "Fresh Kitchen" [level=3]
    - paragraph: Chinese cuisine • Free delivery over $25
    - text: 4.9 20-35 min
  - link "T The Pasta House Italian cuisine • Free delivery over $25 4.9 20-35 min":
    - /url: /customer/eats/922462c9-969b-4527-a6ff-970a9c47592b
    - text: T
    - heading "The Pasta House" [level=3]
    - paragraph: Italian cuisine • Free delivery over $25
    - text: 4.9 20-35 min
  - link "E Effertz - Thompson Cafe Customizable full-range middleware 4.87 20-35 min":
    - /url: /customer/eats/72a643ec-2011-4c65-a6ba-b9444e14df3f
    - text: E
    - heading "Effertz - Thompson Cafe" [level=3]
    - paragraph: Customizable full-range middleware
    - text: 4.87 20-35 min
  - link "T Tokyo Sushi Express Italian cuisine • Free delivery over $25 4.8 20-35 min":
    - /url: /customer/eats/8df737d9-1bcb-4c0e-8b5b-a3af411cf4bc
    - text: T
    - heading "Tokyo Sushi Express" [level=3]
    - paragraph: Italian cuisine • Free delivery over $25
    - text: 4.8 20-35 min
  - link "B Blue Fin Sushi Japanese cuisine • Free delivery over $25 4.8 20-35 min":
    - /url: /customer/eats/ccb0aabf-7bef-49dc-b854-1de2a02b0c58
    - text: B
    - heading "Blue Fin Sushi" [level=3]
    - paragraph: Japanese cuisine • Free delivery over $25
    - text: 4.8 20-35 min
  - link "B Burger Forge American cuisine • Free delivery over $25 4.8 20-35 min":
    - /url: /customer/eats/78c8231e-9ea6-491a-a501-a53848da6d1c
    - text: B
    - heading "Burger Forge" [level=3]
    - paragraph: American cuisine • Free delivery over $25
    - text: 4.8 20-35 min
  - link "T Tokyo Sushi Express Italian cuisine • Free delivery over $25 4.7 20-35 min":
    - /url: /customer/eats/8077463f-15d1-4660-a1a5-cb0c3e8ae717
    - text: T
    - heading "Tokyo Sushi Express" [level=3]
    - paragraph: Italian cuisine • Free delivery over $25
    - text: 4.7 20-35 min
  - link "T Toy, Wiegand and Hackett Cafe Phased dedicated model 4.68 20-35 min":
    - /url: /customer/eats/0970a998-ecbf-43c0-8d54-84d3300f5b5f
    - text: T
    - heading "Toy, Wiegand and Hackett Cafe" [level=3]
    - paragraph: Phased dedicated model
    - text: 4.68 20-35 min
  - link "E El Fuego Tacos Chinese cuisine • Free delivery over $25 4.6 20-35 min":
    - /url: /customer/eats/b247827a-20c0-415f-9173-66d0b7fd71d8
    - text: E
    - heading "El Fuego Tacos" [level=3]
    - paragraph: Chinese cuisine • Free delivery over $25
    - text: 4.6 20-35 min
  - link "P Pizza Napoli Japanese cuisine • Free delivery over $25 4.5 20-35 min":
    - /url: /customer/eats/068c62e3-67c5-4eb4-a725-89b65fd93df2
    - text: P
    - heading "Pizza Napoli" [level=3]
    - paragraph: Japanese cuisine • Free delivery over $25
    - text: 4.5 20-35 min
  - link "T The Rustic Oven Mexican cuisine • Free delivery over $25 4.5 20-35 min":
    - /url: /customer/eats/daa3be3f-3861-411b-8c5c-9ba6e9e63cc8
    - text: T
    - heading "The Rustic Oven" [level=3]
    - paragraph: Mexican cuisine • Free delivery over $25
    - text: 4.5 20-35 min
  - link "G Golden Wok American cuisine • Free delivery over $25 4.3 20-35 min":
    - /url: /customer/eats/6cb0384a-b556-4662-bc0d-929c597a08a7
    - text: G
    - heading "Golden Wok" [level=3]
    - paragraph: American cuisine • Free delivery over $25
    - text: 4.3 20-35 min
  - link "M Murphy, McDermott and Stark Cafe Triple-buffered asynchronous utilisation 4.25 20-35 min":
    - /url: /customer/eats/143a8e64-2592-48b4-b2df-e3fc8ac09d1b
    - text: M
    - heading "Murphy, McDermott and Stark Cafe" [level=3]
    - paragraph: Triple-buffered asynchronous utilisation
    - text: 4.25 20-35 min
  - link "T The Mediterranean Grill Japanese cuisine • Free delivery over $25 4.2 20-35 min":
    - /url: /customer/eats/bb1fdd1f-ada2-4e79-adae-19db3d6e17ee
    - text: T
    - heading "The Mediterranean Grill" [level=3]
    - paragraph: Japanese cuisine • Free delivery over $25
    - text: 4.2 20-35 min
  - link "S Sakura Ramen Japanese cuisine • Free delivery over $25 4.2 20-35 min":
    - /url: /customer/eats/eaa7f7c9-1d9c-4fa9-91e5-b4c9a81bed5c
    - text: S
    - heading "Sakura Ramen" [level=3]
    - paragraph: Japanese cuisine • Free delivery over $25
    - text: 4.2 20-35 min
  - link "P Pho Palace American cuisine • Free delivery over $25 4.1 20-35 min":
    - /url: /customer/eats/333147f5-483b-408c-a04f-f3b7db339911
    - text: P
    - heading "Pho Palace" [level=3]
    - paragraph: American cuisine • Free delivery over $25
    - text: 4.1 20-35 min
  - link "S Smoke & Grill BBQ Mexican cuisine • Free delivery over $25 4 20-35 min":
    - /url: /customer/eats/9458cf59-35d5-44ec-a4fe-8077f3294773
    - text: S
    - heading "Smoke & Grill BBQ" [level=3]
    - paragraph: Mexican cuisine • Free delivery over $25
    - text: 4 20-35 min
  - link "S Sakura Ramen Japanese cuisine • Free delivery over $25 3.9 20-35 min":
    - /url: /customer/eats/53125344-9925-4c61-84f9-00496fc14a9b
    - text: S
    - heading "Sakura Ramen" [level=3]
    - paragraph: Japanese cuisine • Free delivery over $25
    - text: 3.9 20-35 min
  - link "S Seoul Kitchen Italian cuisine • Free delivery over $25 3.9 20-35 min":
    - /url: /customer/eats/39156a47-b2df-41a0-82fb-e0410e37f5f2
    - text: S
    - heading "Seoul Kitchen" [level=3]
    - paragraph: Italian cuisine • Free delivery over $25
    - text: 3.9 20-35 min
  - link "M Mumbai Bites Italian cuisine • Free delivery over $25 3.9 20-35 min":
    - /url: /customer/eats/a4b4fc6e-c501-402b-b409-41cd4a8b63c4
    - text: M
    - heading "Mumbai Bites" [level=3]
    - paragraph: Italian cuisine • Free delivery over $25
    - text: 3.9 20-35 min
  - link "T The Pasta House Italian cuisine • Free delivery over $25 3.8 20-35 min":
    - /url: /customer/eats/0b67ae5d-e916-4dd5-a851-f29873b8cd01
    - text: T
    - heading "The Pasta House" [level=3]
    - paragraph: Italian cuisine • Free delivery over $25
    - text: 3.8 20-35 min
  - link "G Golden Wok American cuisine • Free delivery over $25 3.8 20-35 min":
    - /url: /customer/eats/4f59a64d-dbfb-48a3-ab67-0603f017e150
    - text: G
    - heading "Golden Wok" [level=3]
    - paragraph: American cuisine • Free delivery over $25
    - text: 3.8 20-35 min
  - link "N Noodle Bar Chinese cuisine • Free delivery over $25 3.7 20-35 min":
    - /url: /customer/eats/0dbdc5f2-603b-4b9f-95ba-91dd61d7ee9b
    - text: "N"
    - heading "Noodle Bar" [level=3]
    - paragraph: Chinese cuisine • Free delivery over $25
    - text: 3.7 20-35 min
  - link "F Fresh Kitchen Chinese cuisine • Free delivery over $25 3.7 20-35 min":
    - /url: /customer/eats/503c4153-d083-43a9-8f92-086eaf50bcc2
    - text: F
    - heading "Fresh Kitchen" [level=3]
    - paragraph: Chinese cuisine • Free delivery over $25
    - text: 3.7 20-35 min
  - link "T Taco Republic American cuisine • Free delivery over $25 3.7 20-35 min":
    - /url: /customer/eats/3f1d4488-ade0-4d55-8dbd-915112577765
    - text: T
    - heading "Taco Republic" [level=3]
    - paragraph: American cuisine • Free delivery over $25
    - text: 3.7 20-35 min
  - link "D Dragon Palace Mexican cuisine • Free delivery over $25 3.7 20-35 min":
    - /url: /customer/eats/8cdd4366-afc2-48c9-aebd-29fea96c4787
    - text: D
    - heading "Dragon Palace" [level=3]
    - paragraph: Mexican cuisine • Free delivery over $25
    - text: 3.7 20-35 min
  - link "B Burger Forge American cuisine • Free delivery over $25 3.6 20-35 min":
    - /url: /customer/eats/11c65043-aa6d-4527-9421-5343b2e12dd9
    - text: B
    - heading "Burger Forge" [level=3]
    - paragraph: American cuisine • Free delivery over $25
    - text: 3.6 20-35 min
  - link "G Green Bowl Co. Mexican cuisine • Free delivery over $25 3.6 20-35 min":
    - /url: /customer/eats/14269af1-7302-4d5e-a78b-d2bb410e37ae
    - text: G
    - heading "Green Bowl Co." [level=3]
    - paragraph: Mexican cuisine • Free delivery over $25
    - text: 3.6 20-35 min
  - link "E El Fuego Tacos Chinese cuisine • Free delivery over $25 3.6 20-35 min":
    - /url: /customer/eats/73b010b1-512b-4d84-90f7-1dbfc252b178
    - text: E
    - heading "El Fuego Tacos" [level=3]
    - paragraph: Chinese cuisine • Free delivery over $25
    - text: 3.6 20-35 min
  - link "S Smoke & Grill BBQ Mexican cuisine • Free delivery over $25 3.5 20-35 min":
    - /url: /customer/eats/67687ca7-198b-495b-91f6-a4b1d9926933
    - text: S
    - heading "Smoke & Grill BBQ" [level=3]
    - paragraph: Mexican cuisine • Free delivery over $25
    - text: 3.5 20-35 min
- region "Notifications alt+T"
- alert
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('OneMove Session Hardening & Stale State', () => {
  4  |   test('Cross-tab sign-out logs out all tabs and blocks back-button caching', async ({ browser }) => {
  5  |     const context = await browser.newContext();
  6  |     const tab1 = await context.newPage();
  7  |     
  8  |     // Login on tab 1
  9  |     await tab1.goto('http://localhost:3000/auth/login');
  10 |     await tab1.fill('input[type="email"]', 'customer001@onemove.demo');
  11 |     await tab1.fill('input[type="password"]', 'Customer@001Move');
  12 |     await tab1.click('button[type="submit"]');
  13 |     await tab1.waitForURL('**/customer**');
  14 |     
  15 |     // Open tab 2 and verify we are logged in
  16 |     const tab2 = await context.newPage();
  17 |     await tab2.goto('http://localhost:3000/customer/eats');
> 18 |     await expect(tab2.locator('text="Sign Out"')).toBeVisible();
     |                                                   ^ Error: expect(locator).toBeVisible() failed
  19 |     
  20 |     // Sign out on tab 1
  21 |     await tab1.click('text="Sign Out"');
  22 |     await tab1.waitForURL('**/auth/login');
  23 |     
  24 |     // Attempt an action on tab 2 without refreshing (should fail/redirect due to server action checking auth)
  25 |     // We'll simulate a navigation request since JS might still be loaded
  26 |     await tab2.goto('http://localhost:3000/customer/rides');
  27 |     await tab2.waitForURL('**/auth/login'); // Auth check middleware must bounce us
  28 |     
  29 |     // Attempt to use browser back button on tab 1
  30 |     await tab1.goBack();
  31 |     // It might load from bfcache, but any server interaction should bounce, and middleware should prevent navigation
  32 |     await expect(tab1).toHaveURL(/.*\/auth\/login/);
  33 |   });
  34 | });
  35 | 
```