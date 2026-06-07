const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

(async () => {
  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  const { data: order } = await supabase.from('orders').select('id, status').order('created_at', { ascending: false }).limit(1).single();
  
  console.log(`Latest order: ${order.id}, Status: ${order.status}`);

  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  await page.goto('http://localhost:3000/auth/login');
  await page.fill('input[type="email"]', 'admin@onemove.demo');
  await page.fill('input[type="password"]', 'Demo@12345');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/admin/command-center**');
  
  await page.goto(`http://localhost:3000/admin/orders/${order.id}`);
  await page.waitForLoadState('networkidle');
  
  const content = await page.content();
  console.log('--- HTML CONTENT ---');
  if (content.includes('Order Not Found')) console.log('Found: Order Not Found');
  if (content.includes('completed')) console.log('Found: completed');
  if (content.includes('COMPLETED')) console.log('Found: COMPLETED');
  
  // Extract text from the page
  const text = await page.evaluate(() => document.body.innerText);
  console.log('--- PAGE TEXT ---');
  console.log(text.substring(0, 1000));
  
  await browser.close();
})();
