import { test, expect } from '@playwright/test'
import {
  assertUsablePage,
  attachStrictAudit,
  createDemoOrderForMerchant,
  createDemoOrderForPartner,
  loginAs,
  signOut,
} from './helpers/finalAuditHelpers'

test.describe.serial('Final cross-role user journeys', () => {
  test.setTimeout(120000)

  test('customer can complete ride, eats, grocery, recommendations, and support flows', async ({ page }) => {
    const audit = attachStrictAudit(page)
    await loginAs(page, 'customer')

    await assertUsablePage(page, '/showcase')
    await assertUsablePage(page, '/customer')

    await page.goto('/customer/rides')
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 })
    await page.getByPlaceholder(/Where from/i).fill('JFK')
    await page.getByText('JFK Airport').first().click()
    await page.getByPlaceholder(/Where to/i).fill('Times')
    await page.getByText('Times Square').first().click()
    await expect(page.locator('path.leaflet-interactive')).toHaveCount(1, { timeout: 10000 })
    await expect(page.getByText(/Fare Breakdown/i)).toBeVisible()
    await page.getByRole('button', { name: /Demo Wallet/i }).click()
    await page.getByRole('button', { name: /Request Economy/i }).click()
    await expect(page).toHaveURL(/\/customer\/rides\/[0-9a-f-]+/, { timeout: 20000 })
    await expect(page.getByText(/Ride Tracker/i)).toBeVisible()
    await expect(page.getByText(/Receipt Summary/i)).toBeVisible()

    await page.goto('/customer/eats')
    await page.locator('a[href^="/customer/eats/"]').first().click()
    await page.locator('button:has(.lucide-plus)').first().click()
    await page.getByRole('button', { name: /Go to Checkout/i }).click()
    await expect(page).toHaveURL(/\/customer\/checkout/)
    await page.getByRole('button', { name: /Demo Wallet/i }).click()
    await page.getByRole('button', { name: /Place Order/i }).click()
    await expect(page).toHaveURL(/\/customer\/orders\/[0-9a-f-]+/, { timeout: 20000 })
    await expect(page.getByText(/Order Tracking/i)).toBeVisible()

    await page.goto('/customer/grocery')
    await page.locator('a[href^="/customer/grocery/"]').first().click()
    await page.getByRole('button', { name: /^Add$/ }).first().click()
    await page.getByRole('button', { name: /Go to Checkout/i }).click()
    await page.getByRole('button', { name: /Mock Card/i }).click()
    await page.getByRole('button', { name: /Place Order/i }).click()
    await expect(page).toHaveURL(/\/customer\/orders\/[0-9a-f-]+/, { timeout: 20000 })

    await assertUsablePage(page, '/customer/recommendations')
    await page.goto('/customer/support')
    await page.locator('textarea[name="description"]').fill('Final audit support ticket for deterministic local QA.')
    await page.getByRole('button', { name: /Submit Ticket/i }).click()
    await expect(page).toHaveURL(/\/customer\/support/)
    await expect(page.getByText(/Final audit support ticket/i).first()).toBeVisible({ timeout: 15000 })

    await signOut(page)
    await audit()
  })

  test('merchant can view own queue and advance a fresh demo order', async ({ page }) => {
    const audit = attachStrictAudit(page)
    const orderId = await createDemoOrderForMerchant()
    await loginAs(page, 'merchant')

    await assertUsablePage(page, '/merchant')
    await page.goto('/merchant/orders')
    await expect(page.getByText(`Order ${orderId.split('-')[0]}`)).toBeVisible({ timeout: 15000 })
    const orderCard = () =>
      page
        .getByText(`Order ${orderId.split('-')[0]}`)
        .locator('xpath=ancestor::div[contains(@class,"p-5")][1]')

    await orderCard().getByRole('button', { name: /Accept Order/i }).click()
    await expect(orderCard().getByRole('button', { name: /Start Preparing/i })).toBeVisible({
      timeout: 20000,
    })
    await orderCard().getByRole('button', { name: /Start Preparing/i }).click()
    await expect(orderCard().getByRole('button', { name: /Mark as Ready/i })).toBeVisible({
      timeout: 20000,
    })
    await orderCard().getByRole('button', { name: /Mark as Ready/i }).click()
    await assertUsablePage(page, '/merchant/insights')

    await signOut(page)
    await audit()
  })

  test('partner can accept and update a fresh available job', async ({ page }) => {
    const audit = attachStrictAudit(page)
    const orderId = await createDemoOrderForPartner()
    await loginAs(page, 'partner')

    await assertUsablePage(page, '/partner')
    await page.goto('/partner/jobs')
    await expect(page.getByText(`Order ${orderId.split('-')[0]}`)).toBeVisible({ timeout: 15000 })
    const jobCard = () =>
      page
        .getByText(`Order ${orderId.split('-')[0]}`)
        .locator('xpath=ancestor::div[contains(@class,"p-5")][1]')

    await jobCard().getByRole('button', { name: /Accept Job/i }).click()
    await expect(jobCard().getByRole('button', { name: /Start Transit/i })).toBeVisible({
      timeout: 20000,
    })
    await jobCard().getByRole('button', { name: /Start Transit/i }).click()
    await assertUsablePage(page, '/partner/earnings')
    await assertUsablePage(page, '/partner/insights')

    await signOut(page)
    await audit()
  })
})
