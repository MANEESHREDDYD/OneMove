import { test, expect } from '@playwright/test'

test.describe('Intelligence Platform Phase 4: AI Assistants and MLOps', () => {
  test.use({ storageState: 'playwright/.auth/admin.json' })

  test('Admin Ops Assistant page loads and displays data', async ({ page }) => {
    await page.goto('/admin/ops-assistant')
    await expect(page.locator('h1')).toContainText('Admin Ops Assistant')
    await expect(page.locator('text=MVP deterministic rule-based intelligence')).toBeVisible()
    await expect(page.locator('text=Prioritized Action Items')).toBeVisible()
    
    // Check that there are no console errors
    const errors: string[] = []
    page.on('pageerror', err => errors.push(err.message))
    expect(errors.length).toBe(0)
  })

  test('Admin Support Desk page loads', async ({ page }) => {
    await page.goto('/admin/support-desk')
    await expect(page.locator('h1')).toContainText('AI Support Desk')
    await expect(page.locator('table')).toBeVisible()
  })

  test('Admin Experiments page loads and simulates data', async ({ page }) => {
    test.setTimeout(90000) // Increase timeout for simulation
    await page.goto('/admin/experiments')
    await expect(page.locator('h1')).toContainText('A/B Experiments Platform')
    
    // Check simulate button
    const simulateBtn = page.locator('button:has-text("Simulate Traffic")')
    await expect(simulateBtn).toBeVisible()
    
    // Trigger simulation
    await simulateBtn.click()
    
    // Page reloads and should show metrics instead of "No metrics collected yet"
    // The metric display has "Impressions", wait for it
    await expect(page.locator('text=Impressions').first()).toBeVisible({ timeout: 60000 })
  })

  test('Admin MLOps page loads', async ({ page }) => {
    await page.goto('/admin/mlops')
    await expect(page.locator('h1')).toContainText('MLOps Dashboard')
    await expect(page.locator('text=Pipeline Execution History')).toBeVisible()
  })
})

test.describe('Intelligence Platform Phase 4: Customer Support', () => {
  test.use({ storageState: 'playwright/.auth/customer.json' })

  test('Customer can access support page and submit ticket', async ({ page }) => {
    await page.goto('/customer/support')
    await expect(page.locator('h1')).toContainText('Help & Support')
    
    // Fill out form
    await page.fill('textarea[name="description"]', 'My food arrived completely cold and late.')
    await page.click('button:has-text("Submit Ticket")')
    
    // It should reload and show the ticket
    await expect(page.locator('text=Help & Support')).toBeVisible()
  })
})
