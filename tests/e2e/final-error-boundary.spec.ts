import { test, expect } from '@playwright/test'
import { attachStrictAudit, loginAs } from './helpers/finalAuditHelpers'

test.describe('Final error boundary and invalid-detail audit', () => {
  test('invalid detail IDs recover through safe redirects or empty states without 500s', async ({ page }) => {
    const audit = attachStrictAudit(page)
    await loginAs(page, 'customer')

    await page.goto('/customer/orders/not-a-real-id')
    await expect(page).toHaveURL(/\/customer\/orders/)
    await expect(page.locator('body')).not.toContainText('500 Internal Server Error')

    await page.goto('/customer/rides/not-a-real-id')
    await expect(page.getByText(/Ride not found/i)).toBeVisible()
    await expect(page.locator('body')).not.toContainText('500 Internal Server Error')

    await audit()
  })
})
