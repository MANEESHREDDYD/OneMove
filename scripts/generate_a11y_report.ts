import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import * as fs from 'fs';

const ROUTES = [
  '/',
  '/auth/login',
  '/executive',
  '/network',
  '/admin/system-health',
  '/admin/scenarios',
  '/admin/resilience',
  '/admin/optimize',
  '/admin/decisions',
  '/admin/replay',
  '/admin/evidence',
  '/admin/assistant'
];

async function generateReport() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  let markdown = '# F-028 Accessibility Evidence Report\n\n';
  markdown += '| Route | Critical | Serious | Moderate | Minor | Pass |\n';
  markdown += '|-------|----------|---------|----------|-------|------|\n';

  for (const route of ROUTES) {
    try {
      await page.goto(`http://localhost:3000${route}`, { waitUntil: 'networkidle' });
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();
      
      const critical = results.violations.filter(v => v.impact === 'critical').length;
      const serious = results.violations.filter(v => v.impact === 'serious').length;
      const moderate = results.violations.filter(v => v.impact === 'moderate').length;
      const minor = results.violations.filter(v => v.impact === 'minor').length;
      
      const passed = (critical === 0 && serious === 0) ? '✅' : '❌';

      markdown += `| \`${route}\` | ${critical} | ${serious} | ${moderate} | ${minor} | ${passed} |\n`;
    } catch (e) {
      markdown += `| \`${route}\` | ERR | ERR | ERR | ERR | ❌ |\n`;
    }
  }

  await browser.close();
  
  const artifactPath = 'C:\\Users\\md200\\.gemini\\antigravity-ide\\brain\\05848ff4-6a1e-406c-8d2c-d430d95ae125\\a11y_evidence_F-028.md';
  fs.writeFileSync(artifactPath, markdown);
  console.log(`Report generated at ${artifactPath}`);
}

generateReport();
