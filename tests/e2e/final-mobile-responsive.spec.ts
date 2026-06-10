import { test, expect } from '@playwright/test'
import { assertUsablePage, attachStrictAudit, loginAs } from './helpers/finalAuditHelpers'

async function expectNoHorizontalOverflow(page: import('@playwright/test').Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(12)
}

test.describe('Final mobile responsive audit', () => {
  test('customer mobile routes remain usable', async ({ page }) => {
    const audit = attachStrictAudit(page)
    await page.setViewportSize({ width: 390, height: 844 })
    await loginAs(page, 'customer')

    for (const route of ['/showcase', '/customer', '/customer/rides', '/customer/orders']) {
      await assertUsablePage(page, route)
      await expectNoHorizontalOverflow(page)
    }

    await audit()
  })

  test('admin health and analytics mobile routes remain usable', async ({ page }) => {
    const audit = attachStrictAudit(page)
    await page.setViewportSize({ width: 390, height: 844 })
    await loginAs(page, 'admin')

    for (const route of ['/admin/system-health', '/admin/analytics', '/admin/mlops', '/admin/experiments']) {
      await assertUsablePage(page, route)
      await expectNoHorizontalOverflow(page)
    }

    await audit()
  })
})
