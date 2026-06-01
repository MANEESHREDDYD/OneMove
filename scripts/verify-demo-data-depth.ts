import { Client } from 'pg';
import * as path from 'path';
import * as fs from 'fs';

const envPath = path.join(process.cwd(), '.env.local');
const envVars: Record<string, string> = {};
if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.substring(0, eqIdx).trim();
    let value = trimmed.substring(eqIdx + 1).trim();
    if (value.startsWith('"') && value.endsWith('"')) value = value.substring(1, value.length - 1);
    envVars[key] = value;
  }
}

const directUrl = envVars['DIRECT_URL'];
if (!directUrl) { console.error("Missing DIRECT_URL"); process.exit(1); }

interface Check { label: string; query: string; min: number; }

const CHECKS: Check[] = [
  { label: 'Customers (profiles.role=customer)', query: "SELECT COUNT(*) FROM profiles WHERE role='customer'", min: 50 },
  { label: 'Partners (profiles.role=driver)', query: "SELECT COUNT(*) FROM profiles WHERE role='driver'", min: 50 },
  { label: 'Merchants (profiles.role=merchant)', query: "SELECT COUNT(*) FROM profiles WHERE role='merchant'", min: 10 },
  { label: 'Merchants (table)', query: "SELECT COUNT(*) FROM merchants", min: 20 },
  { label: 'Restaurants (category=restaurant)', query: "SELECT COUNT(*) FROM merchants WHERE category='restaurant'", min: 10 },
  { label: 'Grocery Stores (category=grocery)', query: "SELECT COUNT(*) FROM merchants WHERE category='grocery'", min: 10 },
  { label: 'Products/Menu Items', query: "SELECT COUNT(*) FROM products", min: 200 },
  { label: 'Ride Orders', query: "SELECT COUNT(*) FROM orders WHERE service_type='ride'", min: 20 },
  { label: 'Eats Orders', query: "SELECT COUNT(*) FROM orders WHERE service_type='eats'", min: 20 },
  { label: 'Grocery Orders', query: "SELECT COUNT(*) FROM orders WHERE service_type='grocery'", min: 20 },
  { label: 'Courier Orders', query: "SELECT COUNT(*) FROM orders WHERE service_type='courier'", min: 20 },
  { label: 'Order Items', query: "SELECT COUNT(*) FROM order_items", min: 50 },
  { label: 'Payments', query: "SELECT COUNT(*) FROM payments", min: 50 },
  { label: 'Analytics Events', query: "SELECT COUNT(*) FROM analytics_events", min: 50 },
  { label: 'ML Score Logs', query: "SELECT COUNT(*) FROM ml_score_logs", min: 20 },
];

async function run() {
  const client = new Client({ connectionString: directUrl });
  await client.connect();
  console.log("✅ Connected.\n");
  console.log("=".repeat(70));
  console.log("DEMO DATA DEPTH VERIFICATION");
  console.log("=".repeat(70));

  let allPassed = true;
  for (const check of CHECKS) {
    try {
      const { rows } = await client.query(check.query);
      const count = parseInt(rows[0].count, 10);
      const pass = count >= check.min;
      if (!pass) allPassed = false;
      console.log(`${pass ? '✅' : '❌'} ${check.label}: ${count} (min: ${check.min})`);
    } catch (err: any) {
      console.log(`❌ ${check.label}: ERROR - ${err.message}`);
      allPassed = false;
    }
  }

  console.log("\n" + "=".repeat(70));
  console.log(allPassed ? "✅ ALL CHECKS PASSED" : "❌ SOME CHECKS FAILED - Run: npm run seed:production-demo");
  console.log("=".repeat(70));

  await client.end();
}

run().catch(err => { console.error(err); process.exit(1); });
