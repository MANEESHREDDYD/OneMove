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
    - complementary [ref=e3]:
      - link "OneMove" [ref=e5]:
        - /url: /
      - navigation [ref=e6]:
        - link "Command Center" [ref=e7]:
          - /url: /admin/command-center
          - img [ref=e8]
          - generic [ref=e13]: Command Center
        - link "Analytics" [ref=e14]:
          - /url: /admin/analytics
          - img [ref=e15]
          - generic [ref=e18]: Analytics
        - link "ML Lab" [ref=e19]:
          - /url: /admin/ml-lab
          - img [ref=e20]
          - generic [ref=e22]: ML Lab
        - link "Compliance" [ref=e23]:
          - /url: /admin/compliance
          - img [ref=e24]
          - generic [ref=e26]: Compliance
        - link "Ops Assistant" [ref=e27]:
          - /url: /admin/ops-assistant
          - img [ref=e28]
          - generic [ref=e36]: Ops Assistant
        - link "Support Desk" [ref=e37]:
          - /url: /admin/support-desk
          - img [ref=e38]
          - generic [ref=e40]: Support Desk
        - link "Experiments" [ref=e41]:
          - /url: /admin/experiments
          - img [ref=e42]
          - generic [ref=e44]: Experiments
        - link "MLOps" [ref=e45]:
          - /url: /admin/mlops
          - img [ref=e46]
          - generic [ref=e48]: MLOps
    - main [ref=e49]:
      - generic [ref=e51]:
        - generic [ref=e52]:
          - generic [ref=e53]:
            - img [ref=e54]
            - generic [ref=e56]:
              - heading "A/B Experiments Platform" [level=1] [ref=e57]
              - paragraph [ref=e58]: MVP directional experiment readout; not a production statistical inference engine.
          - button "Simulate Traffic" [ref=e60]:
            - img [ref=e61]
            - text: Simulate Traffic
        - generic [ref=e67]:
          - generic [ref=e68]:
            - generic [ref=e69]:
              - heading "Dynamic Delivery Fee Test" [level=2] [ref=e70]
              - paragraph [ref=e71]: Testing if dynamic delivery fees based on demand increases overall conversion vs flat fees.
            - generic [ref=e72]: ACTIVE
          - generic [ref=e74]:
            - generic [ref=e75]:
              - generic [ref=e76]:
                - heading "Treatment (Dynamic)" [level=3] [ref=e77]
                - generic [ref=e78]: 50% Alloc
              - generic [ref=e79]:
                - generic [ref=e80]:
                  - generic [ref=e81]: Impressions
                  - generic [ref=e82]: "42"
                - generic [ref=e83]:
                  - generic [ref=e84]: Conversions
                  - generic [ref=e85]: "13"
                - generic [ref=e86]:
                  - generic [ref=e87]: Conv. Rate
                  - generic [ref=e88]: 31.0%
                - generic [ref=e89]:
                  - generic [ref=e90]: Revenue
                  - generic [ref=e91]: $536.00
              - generic [ref=e93]: continue (winning)
            - generic [ref=e94]:
              - generic [ref=e95]:
                - heading "Control (Flat Fee)" [level=3] [ref=e96]
                - generic [ref=e97]: 50% Alloc
              - generic [ref=e98]:
                - generic [ref=e99]:
                  - generic [ref=e100]: Impressions
                  - generic [ref=e101]: "58"
                - generic [ref=e102]:
                  - generic [ref=e103]: Conversions
                  - generic [ref=e104]: "13"
                - generic [ref=e105]:
                  - generic [ref=e106]: Conv. Rate
                  - generic [ref=e107]: 22.4%
                - generic [ref=e108]:
                  - generic [ref=e109]: Revenue
                  - generic [ref=e110]: $479.00
              - generic [ref=e112]: needs more data
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e118] [cursor=pointer]:
    - generic [ref=e121]:
      - text: Compiling
      - generic [ref=e122]:
        - generic [ref=e123]: .
        - generic [ref=e124]: .
        - generic [ref=e125]: .
  - alert [ref=e126]
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