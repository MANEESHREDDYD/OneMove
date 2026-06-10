import { test, expect, chromium, Browser, BrowserContext } from '@playwright/test';
import { assertNoConsoleErrors } from './helpers/assertNoConsoleErrors';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

test.describe('OneMove Ride Flow', () => {
  let browser: Browser;
  let customerCtx: BrowserContext;
  let partnerCtx: BrowserContext;
  let adminCtx: BrowserContext;

  test.beforeAll(async () => {
    browser = await chromium.launch();
  });

  test.afterAll(async () => {
    await browser.close();
  });

  test('E2E Ride Booking across roles', async () => {
    customerCtx = await browser.newContext();
    partnerCtx = await browser.newContext();
    adminCtx = await browser.newContext();

    const customerPage = await customerCtx.newPage();
    const partnerPage = await partnerCtx.newPage();
    const adminPage = await adminCtx.newPage();

    const checkCustomerErrors = assertNoConsoleErrors(customerPage);
    const checkPartnerErrors = assertNoConsoleErrors(partnerPage);
    const checkAdminErrors = assertNoConsoleErrors(adminPage);

    // Login Roles
    await Promise.all([
      (async () => {
        await customerPage.goto('http://localhost:3000/auth/login');
        await customerPage.fill('input[type="email"]', 'customer001@onemove.demo');
        await customerPage.fill('input[type="password"]', 'Customer@001Move');
        await customerPage.click('button[type="submit"]');
        await customerPage.waitForURL('**/customer**');
      })(),
      (async () => {
        await partnerPage.goto('http://localhost:3000/auth/login');
        await partnerPage.fill('input[type="email"]', 'partner001@onemove.demo');
        await partnerPage.fill('input[type="password"]', 'Partner@001Move');
        await partnerPage.click('button[type="submit"]');
        await partnerPage.waitForURL('**/partner**');
      })(),
      (async () => {
        await adminPage.goto('http://localhost:3000/auth/login');
        await adminPage.fill('input[type="email"]', 'admin@onemove.demo');
        await adminPage.fill('input[type="password"]', 'Demo@12345');
        await adminPage.click('button[type="submit"]');
        await adminPage.waitForURL('**/admin/command-center**');
      })(),
    ]);

    // Reset active jobs so partner can accept a new one
    const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);
    await supabase.from('orders').update({ status: 'completed' }).in('status', ['accepted', 'in_transit', 'arrived', 'started', 'picked_up']);

    // Customer books ride
    await customerPage.goto('http://localhost:3000/customer/rides');
    await customerPage.fill('input[placeholder*="Where from?"]', 'JFK');
    await customerPage.click('text=JFK Airport');
    await customerPage.fill('input[placeholder*="Where to?"]', 'Times Square');
    await customerPage.click('text=Times Square');

    // Select Economy Ride (Economy is the default selected tier)
    await customerPage.locator('button', { hasText: 'Request Economy' }).click();

    // Ensure ride is created and we are redirected to tracking
    await customerPage.waitForURL(/.*\/customer\/rides\/.*/);

    await customerPage.waitForURL(/.*\/customer\/rides\/.*/);
    const rideUrl = customerPage.url();
    const urlObj = new URL(rideUrl);
    const rideId = urlObj.pathname.split('/').pop()!;
    console.log("RIDE ID IS:", rideId);
    expect(rideId).toBeDefined();

    // Partner accepts ride
    await partnerPage.reload();
    await partnerPage.locator('button', { hasText: 'Accept Job' }).first().click();
    await partnerPage.locator('button', { hasText: 'Arrived at Pickup' }).click();
    await partnerPage.locator('button', { hasText: 'Start Ride' }).click();
    await partnerPage.locator('button', { hasText: 'Complete Ride' }).click();
    // The button text changes to Updating... so we can't wait for it to be hidden. Wait for the Active Job section to disappear.
    await partnerPage.locator('text=Active Job').first().waitFor({ state: 'hidden' });

    // Admin views ride details
    await adminPage.goto(`http://localhost:3000/admin/orders/${rideId}`);
    try {
      await expect(adminPage.getByText('completed', { exact: false }).first()).toBeVisible({ timeout: 5000 });
    } catch (e) {
      console.log("Admin Page Content:", await adminPage.content());
      throw e;
    }

    checkCustomerErrors();
    checkPartnerErrors();
    checkAdminErrors();
  });
});
