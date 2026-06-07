# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-intelligence-platform-phase4.spec.ts >> Intelligence Platform Phase 4: AI Assistants and MLOps >> Admin Experiments page loads and simulates data
- Location: tests\e2e\onemove-intelligence-platform-phase4.spec.ts:24:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: expect.toBeVisible: Target page, context or browser has been closed
```

# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [ref=e2]:
    - complementary [ref=e3]:
      - link "OneMove" [ref=e5] [cursor=pointer]:
        - /url: /
      - navigation [ref=e6]:
        - link "Command Center" [ref=e7] [cursor=pointer]:
          - /url: /admin/command-center
          - img [ref=e8]
          - generic [ref=e13]: Command Center
        - link "Analytics" [ref=e14] [cursor=pointer]:
          - /url: /admin/analytics
          - img [ref=e15]
          - generic [ref=e18]: Analytics
        - link "ML Lab" [ref=e19] [cursor=pointer]:
          - /url: /admin/ml-lab
          - img [ref=e20]
          - generic [ref=e24]: ML Lab
        - link "Compliance" [ref=e25] [cursor=pointer]:
          - /url: /admin/compliance
          - img [ref=e26]
          - generic [ref=e28]: Compliance
        - link "Ops Assistant" [ref=e29] [cursor=pointer]:
          - /url: /admin/ops-assistant
          - img [ref=e30]
          - generic [ref=e39]: Ops Assistant
        - link "Support Desk" [ref=e40] [cursor=pointer]:
          - /url: /admin/support-desk
          - img [ref=e41]
          - generic [ref=e43]: Support Desk
        - link "Experiments" [ref=e44] [cursor=pointer]:
          - /url: /admin/experiments
          - img [ref=e45]
          - generic [ref=e49]: Experiments
        - link "MLOps" [ref=e50] [cursor=pointer]:
          - /url: /admin/mlops
          - img [ref=e51]
          - generic [ref=e53]: MLOps
    - main [ref=e54]:
      - generic [ref=e56]:
        - generic [ref=e57]:
          - generic [ref=e58]:
            - img [ref=e59]
            - generic [ref=e63]:
              - heading "A/B Experiments Platform" [level=1] [ref=e64]
              - paragraph [ref=e65]: MVP directional experiment readout; not a production statistical inference engine.
          - button "Simulate Traffic" [active] [ref=e67]:
            - img [ref=e68]
            - text: Simulate Traffic
        - generic [ref=e74]:
          - generic [ref=e75]:
            - generic [ref=e76]:
              - heading "Dynamic Delivery Fee Test" [level=2] [ref=e77]
              - paragraph [ref=e78]: Testing if dynamic delivery fees based on demand increases overall conversion vs flat fees.
            - generic [ref=e79]: ACTIVE
          - generic [ref=e81]:
            - generic [ref=e82]:
              - generic [ref=e83]:
                - heading "Treatment (Dynamic)" [level=3] [ref=e84]
                - generic [ref=e85]: 50% Alloc
              - generic [ref=e86]:
                - generic [ref=e87]:
                  - generic [ref=e88]: Impressions
                  - generic [ref=e89]: "42"
                - generic [ref=e90]:
                  - generic [ref=e91]: Conversions
                  - generic [ref=e92]: "13"
                - generic [ref=e93]:
                  - generic [ref=e94]: Conv. Rate
                  - generic [ref=e95]: 31.0%
                - generic [ref=e96]:
                  - generic [ref=e97]: Revenue
                  - generic [ref=e98]: $536.00
              - generic [ref=e100]: continue (winning)
            - generic [ref=e101]:
              - generic [ref=e102]:
                - heading "Control (Flat Fee)" [level=3] [ref=e103]
                - generic [ref=e104]: 50% Alloc
              - generic [ref=e105]:
                - generic [ref=e106]:
                  - generic [ref=e107]: Impressions
                  - generic [ref=e108]: "58"
                - generic [ref=e109]:
                  - generic [ref=e110]: Conversions
                  - generic [ref=e111]: "13"
                - generic [ref=e112]:
                  - generic [ref=e113]: Conv. Rate
                  - generic [ref=e114]: 22.4%
                - generic [ref=e115]:
                  - generic [ref=e116]: Revenue
                  - generic [ref=e117]: $479.00
              - generic [ref=e119]: needs more data
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e125] [cursor=pointer]:
    - generic [ref=e128]:
      - text: Compiling
      - generic [ref=e129]:
        - generic [ref=e130]: .
        - generic [ref=e131]: .
        - generic [ref=e132]: .
  - alert [ref=e133]
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Intelligence Platform Phase 4: AI Assistants and MLOps', () => {
  4  |   test.use({ storageState: 'playwright/.auth/admin.json' })
  5  | 
  6  |   test('Admin Ops Assistant page loads and displays data', async ({ page }) => {
  7  |     await page.goto('/admin/ops-assistant')
  8  |     await expect(page.locator('h1')).toContainText('Admin Ops Assistant')
  9  |     await expect(page.locator('text=MVP deterministic rule-based intelligence')).toBeVisible()
  10 |     await expect(page.locator('text=Prioritized Action Items')).toBeVisible()
  11 |     
  12 |     // Check that there are no console errors
  13 |     const errors: string[] = []
  14 |     page.on('pageerror', err => errors.push(err.message))
  15 |     expect(errors.length).toBe(0)
  16 |   })
  17 | 
  18 |   test('Admin Support Desk page loads', async ({ page }) => {
  19 |     await page.goto('/admin/support-desk')
  20 |     await expect(page.locator('h1')).toContainText('AI Support Desk')
  21 |     await expect(page.locator('table')).toBeVisible()
  22 |   })
  23 | 
  24 |   test('Admin Experiments page loads and simulates data', async ({ page }) => {
  25 |     await page.goto('/admin/experiments')
  26 |     await expect(page.locator('h1')).toContainText('A/B Experiments Platform')
  27 |     
  28 |     // Check simulate button
  29 |     const simulateBtn = page.locator('button:has-text("Simulate Traffic")')
  30 |     await expect(simulateBtn).toBeVisible()
  31 |     
  32 |     // Trigger simulation
  33 |     await simulateBtn.click()
  34 |     
  35 |     // Page reloads and should show metrics
> 36 |     await expect(page.locator('text=A/B Experiments Platform')).toBeVisible()
     |                                                                 ^ Error: expect.toBeVisible: Target page, context or browser has been closed
  37 |   })
  38 | 
  39 |   test('Admin MLOps page loads', async ({ page }) => {
  40 |     await page.goto('/admin/mlops')
  41 |     await expect(page.locator('h1')).toContainText('MLOps Dashboard')
  42 |     await expect(page.locator('text=Pipeline Execution History')).toBeVisible()
  43 |   })
  44 | })
  45 | 
  46 | test.describe('Intelligence Platform Phase 4: Customer Support', () => {
  47 |   test.use({ storageState: 'playwright/.auth/customer.json' })
  48 | 
  49 |   test('Customer can access support page and submit ticket', async ({ page }) => {
  50 |     await page.goto('/customer/support')
  51 |     await expect(page.locator('h1')).toContainText('Help & Support')
  52 |     
  53 |     // Fill out form
  54 |     await page.fill('textarea[name="description"]', 'My food arrived completely cold and late.')
  55 |     await page.click('button:has-text("Submit Ticket")')
  56 |     
  57 |     // It should reload and show the ticket
  58 |     await expect(page.locator('text=Help & Support')).toBeVisible()
  59 |   })
  60 | })
  61 | 
```