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
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - main [ref=e3]:
      - generic [ref=e5]:
        - generic [ref=e6]:
          - generic [ref=e7]:
            - img [ref=e8]
            - generic [ref=e10]:
              - heading "A/B Experiments Platform" [level=1] [ref=e11]
              - paragraph [ref=e12]: MVP directional experiment readout; not a production statistical inference engine.
          - button "Simulate Traffic" [ref=e14]:
            - img [ref=e15]
            - text: Simulate Traffic
        - generic [ref=e21]:
          - generic [ref=e22]:
            - generic [ref=e23]:
              - heading "Dynamic Delivery Fee Test" [level=2] [ref=e24]
              - paragraph [ref=e25]: Testing if dynamic delivery fees based on demand increases overall conversion vs flat fees.
            - generic [ref=e26]: ACTIVE
          - generic [ref=e28]:
            - generic [ref=e29]:
              - generic [ref=e30]:
                - heading "Treatment (Dynamic)" [level=3] [ref=e31]
                - generic [ref=e32]: 50% Alloc
              - generic [ref=e33]:
                - generic [ref=e34]:
                  - generic [ref=e35]: Impressions
                  - generic [ref=e36]: "42"
                - generic [ref=e37]:
                  - generic [ref=e38]: Conversions
                  - generic [ref=e39]: "13"
                - generic [ref=e40]:
                  - generic [ref=e41]: Conv. Rate
                  - generic [ref=e42]: 31.0%
                - generic [ref=e43]:
                  - generic [ref=e44]: Revenue
                  - generic [ref=e45]: $536.00
              - generic [ref=e47]: continue (winning)
            - generic [ref=e48]:
              - generic [ref=e49]:
                - heading "Control (Flat Fee)" [level=3] [ref=e50]
                - generic [ref=e51]: 50% Alloc
              - generic [ref=e52]:
                - generic [ref=e53]:
                  - generic [ref=e54]: Impressions
                  - generic [ref=e55]: "58"
                - generic [ref=e56]:
                  - generic [ref=e57]: Conversions
                  - generic [ref=e58]: "13"
                - generic [ref=e59]:
                  - generic [ref=e60]: Conv. Rate
                  - generic [ref=e61]: 22.4%
                - generic [ref=e62]:
                  - generic [ref=e63]: Revenue
                  - generic [ref=e64]: $479.00
              - generic [ref=e66]: needs more data
    - navigation [ref=e67]:
      - generic [ref=e68]:
        - link "Command Center" [ref=e69]:
          - /url: /admin/command-center
          - img [ref=e70]
          - generic [ref=e75]: Command Center
        - link "Analytics" [ref=e76]:
          - /url: /admin/analytics
          - img [ref=e77]
          - generic [ref=e80]: Analytics
        - link "ML Lab" [ref=e81]:
          - /url: /admin/ml-lab
          - img [ref=e82]
          - generic [ref=e84]: ML Lab
        - link "Compliance" [ref=e85]:
          - /url: /admin/compliance
          - img [ref=e86]
          - generic [ref=e88]: Compliance
        - link "Ops Assistant" [ref=e89]:
          - /url: /admin/ops-assistant
          - img [ref=e90]
          - generic [ref=e98]: Ops Assistant
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e104] [cursor=pointer]:
    - generic [ref=e107]:
      - text: Compiling
      - generic [ref=e108]:
        - generic [ref=e109]: .
        - generic [ref=e110]: .
        - generic [ref=e111]: .
  - alert [ref=e112]
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