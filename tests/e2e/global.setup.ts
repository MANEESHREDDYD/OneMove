import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFileCustomer = path.join(__dirname, '../../playwright/.auth/customer.json');
const authFileAdmin = path.join(__dirname, '../../playwright/.auth/admin.json');
const authFilePartner = path.join(__dirname, '../../playwright/.auth/partner.json');
const authFileMerchant = path.join(__dirname, '../../playwright/.auth/merchant.json');

setup('authenticate customer', async ({ page }) => {
  if (process.env.TENANT_A_EMAIL) return; // Skip in demo mode
  await page.goto('http://localhost:3000/auth/login');
  await page.fill('input[type="email"]', 'customer001@onemove.demo');
  await page.fill('input[type="password"]', 'Customer@001Move');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/customer**');
  await page.context().storageState({ path: authFileCustomer });
});

setup('authenticate admin', async ({ page }) => {
  const email = process.env.TENANT_A_EMAIL || 'admin001@onemove.demo';
  const password = process.env.TENANT_A_PASSWORD || 'Admin@001Move';
  await page.goto('http://localhost:3000/auth/login');
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/admin**');
  await page.context().storageState({ path: authFileAdmin });
});

setup('authenticate partner', async ({ page }) => {
  if (process.env.TENANT_A_EMAIL) return; // Skip in demo mode
  await page.goto('http://localhost:3000/auth/login');
  await page.fill('input[type="email"]', 'partner001@onemove.demo');
  await page.fill('input[type="password"]', 'Partner@001Move');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/partner**');
  await page.context().storageState({ path: authFilePartner });
});

setup('authenticate merchant', async ({ page }) => {
  if (process.env.TENANT_A_EMAIL) return; // Skip in demo mode
  await page.goto('http://localhost:3000/auth/login');
  await page.fill('input[type="email"]', 'merchant001@onemove.demo');
  await page.fill('input[type="password"]', 'Merchant@001Move');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/merchant**');
  await page.context().storageState({ path: authFileMerchant });
});
