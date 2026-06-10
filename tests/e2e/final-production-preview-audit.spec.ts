import { test, expect } from '@playwright/test'
import { assertUsablePage, attachStrictAudit, loginAs, signOut } from './helpers/finalAuditHelpers'

test.describe('Final production-preview route audit', () => {
  test('public and protected route behavior is production-preview safe', async ({ browser }) => {
    const anonymous = await browser.newPage()
    const anonymousAudit = attachStrictAudit(anonymous)
    await anonymous.goto('/admin/command-center')
    await expect(anonymous).toHaveURL(/\/auth\/login/)
    await anonymousAudit()
    await anonymous.close()
  })

  test('admin intelligence routes render without blank pages or 500s', async ({ page }) => {
    const audit = attachStrictAudit(page)
    await loginAs(page, 'admin')

    const routes = [
      '/admin/command-center',
      '/admin/data-platform',
      '/admin/analytics',
      '/admin/demand-intelligence',
      '/admin/dispatch-optimizer',
      '/admin/risk-center',
      '/admin/recommendation-lab',
      '/admin/customer-segments',
      '/admin/merchant-intelligence',
      '/admin/partner-intelligence',
      '/admin/ops-assistant',
      '/admin/support-desk',
      '/admin/experiments',
      '/admin/mlops',
      '/admin/architecture',
      '/admin/system-health',
    ]

    for (const route of routes) {
      await assertUsablePage(page, route)
    }

    await signOut(page)
    await audit()
  })
})
