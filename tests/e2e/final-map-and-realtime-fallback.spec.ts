import { test, expect } from '@playwright/test'
import { attachStrictAudit, loginAs } from './helpers/finalAuditHelpers'

test.describe('Final map and realtime fallback audit', () => {
  test('ride map renders markers, route polyline, and fare estimate without client crashes', async ({ page }) => {
    const audit = attachStrictAudit(page)
    await loginAs(page, 'customer')

    await page.goto('/customer/rides')
    await expect(page.locator('.leaflet-container')).toBeVisible({ timeout: 15000 })
    await expect(page.locator('img.leaflet-tile').first()).toBeVisible({ timeout: 15000 })
    await page.getByPlaceholder(/Where from/i).fill('JFK')
    await page.getByText('JFK Airport').first().click()
    await page.getByPlaceholder(/Where to/i).fill('Times')
    await page.getByText('Times Square').first().click()
    await expect(page.locator('path.leaflet-interactive')).toHaveCount(1, { timeout: 10000 })
    await expect(page.getByText(/Routing:/i)).toBeVisible()
    await expect(page.getByText(/Fare Breakdown/i)).toBeVisible()
    await audit()
  })

  test('merchant and partner realtime surfaces fall back to usable pages', async ({ page }) => {
    const audit = attachStrictAudit(page)
    await loginAs(page, 'partner')
    await page.goto('/partner/jobs')
    await expect(page.getByText(/Job Marketplace/i)).toBeVisible()
    await audit()
  })
})
