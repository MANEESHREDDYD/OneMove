# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-negative-flows.spec.ts >> OneMove E2E Negative & Edge Case Flows >> Ride Booking: Invalid inputs block booking
- Location: tests\e2e\onemove-negative-flows.spec.ts:31:7

# Error details

```
Error: expect(locator).toBeDisabled() failed

Locator: locator('button:has-text("Book Ride")')
Expected: disabled
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeDisabled" with timeout 5000ms
  - waiting for locator('button:has-text("Book Ride")')

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
  - heading "Request a Ride" [level=1]
  - paragraph: Where are you heading today?
  - button "Zoom in"
  - button "Zoom out"
  - link "Leaflet":
    - /url: https://leafletjs.com
  - text: ©
  - link "OpenStreetMap":
    - /url: https://www.openstreetmap.org/copyright
  - text: Pickup Location
  - textbox "Where from? (e.g. JFK Airport)"
  - text: Dropoff Location
  - textbox "Where to? (e.g. Times Square)"
  - paragraph: Select your pickup and dropoff locations to see live estimates.
  - button "Enter Destinations" [disabled]
- region "Notifications alt+T"
- alert
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test.describe('OneMove E2E Negative & Edge Case Flows', () => {
  4  |   test('Auth Abuse: Stale session and manual URL entry rejection', async ({ page, context }) => {
  5  |     // Login as customer
  6  |     await page.goto('http://localhost:3000/auth/login');
  7  |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  8  |     await page.fill('input[type="password"]', 'Customer@001Move');
  9  |     await page.click('button[type="submit"]');
  10 |     
  11 |     // Wait for redirect
  12 |     await page.waitForURL('**/customer**');
  13 |     
  14 |     // Sign out
  15 |     await page.click('text="Sign Out"');
  16 |     await page.waitForURL('**/auth/login');
  17 |     
  18 |     // Attempt to navigate back via URL
  19 |     await page.goto('http://localhost:3000/customer');
  20 |     
  21 |     // Should be rejected back to login
  22 |     await page.waitForURL('**/auth/login');
  23 |     
  24 |     // Test bad credentials
  25 |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  26 |     await page.fill('input[type="password"]', 'WrongPassword123');
  27 |     await page.click('button[type="submit"]');
  28 |     await expect(page.locator('text="Invalid login credentials"')).toBeVisible();
  29 |   });
  30 | 
  31 |   test('Ride Booking: Invalid inputs block booking', async ({ page }) => {
  32 |     await page.goto('http://localhost:3000/auth/login');
  33 |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  34 |     await page.fill('input[type="password"]', 'Customer@001Move');
  35 |     await page.click('button[type="submit"]');
  36 |     
  37 |     await page.waitForURL('**/customer**');
  38 |     await page.goto('http://localhost:3000/customer/rides');
  39 |     
  40 |     // Button should be disabled initially
  41 |     const bookButton = page.locator('button:has-text("Book Ride")');
> 42 |     await expect(bookButton).toBeDisabled();
     |                              ^ Error: expect(locator).toBeDisabled() failed
  43 |     
  44 |     // Put same pickup and dropoff
  45 |     await page.fill('input[placeholder*="Where from?"]', 'JFK');
  46 |     await page.click('text=JFK Airport');
  47 |     
  48 |     await page.fill('input[placeholder*="Where to?"]', 'JFK');
  49 |     await page.click('text=JFK Airport');
  50 |     
  51 |     // Wait and assert that the estimate doesn't pop up or button stays disabled due to distance 0
  52 |     // The UI should either show an error or keep it disabled.
  53 |     // For now we just verify it doesn't proceed to a valid checkout state immediately
  54 |     await page.waitForTimeout(1000);
  55 |   });
  56 | 
  57 |   test('Checkout: Empty cart behavior', async ({ page }) => {
  58 |     await page.goto('http://localhost:3000/auth/login');
  59 |     await page.fill('input[type="email"]', 'customer001@onemove.demo');
  60 |     await page.fill('input[type="password"]', 'Customer@001Move');
  61 |     await page.click('button[type="submit"]');
  62 |     
  63 |     // Force direct navigate to a merchant without adding items
  64 |     await page.goto('http://localhost:3000/customer/eats');
  65 |     await page.waitForSelector('a[href^="/customer/eats/"]');
  66 |     await page.click('a[href^="/customer/eats/"]');
  67 |     
  68 |     // Assuming there's a cart view, the Place Order should be hidden or disabled
  69 |     const placeOrderBtn = page.locator('button:has-text("Place Order")');
  70 |     if (await placeOrderBtn.isVisible()) {
  71 |         await expect(placeOrderBtn).toBeDisabled();
  72 |     }
  73 |   });
  74 | });
  75 | 
```