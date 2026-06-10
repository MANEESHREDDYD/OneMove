 
import { Client } from 'pg';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

async function checkDataIntegrity() {
  const client = new Client({ connectionString: process.env.DIRECT_URL });
  await client.connect();

  console.log('======================================================================');
  console.log('DEBUG: DATA INTEGRITY (ADVANCED QA)');
  console.log('======================================================================');

  const rules = [
    { name: 'orders missing customer_id', sql: 'SELECT COUNT(*) FROM orders WHERE is_demo = true AND customer_id IS NULL' },
    { name: 'eats/grocery missing merchant_id', sql: "SELECT COUNT(*) FROM orders WHERE is_demo = true AND service_type IN ('eats', 'grocery') AND merchant_id IS NULL" },
    { name: 'orders missing payment record', sql: 'SELECT COUNT(*) FROM orders o LEFT JOIN payments p ON o.id = p.order_id WHERE o.is_demo = true AND p.id IS NULL' },
    { name: 'eats/grocery missing order_items', sql: "SELECT COUNT(*) FROM orders o LEFT JOIN order_items oi ON o.id = oi.order_id WHERE o.is_demo = true AND o.service_type IN ('eats', 'grocery') AND oi.id IS NULL" },
    { name: 'rides missing pickup/dropoff', sql: "SELECT COUNT(*) FROM orders WHERE is_demo = true AND service_type = 'ride' AND (pickup_location IS NULL OR dropoff_location IS NULL)" },
    { name: 'courier missing pickup/dropoff', sql: "SELECT COUNT(*) FROM orders WHERE is_demo = true AND service_type = 'courier' AND (pickup_location IS NULL OR dropoff_location IS NULL)" },
    { name: 'status_events missing parent record', sql: 'SELECT COUNT(*) FROM order_status_events s LEFT JOIN orders o ON s.order_id = o.id WHERE s.is_demo = true AND o.id IS NULL' },
    { name: 'payments orphaned', sql: 'SELECT COUNT(*) FROM payments p LEFT JOIN orders o ON p.order_id = o.id WHERE p.is_demo = true AND o.id IS NULL' },
    { name: 'analytics_events orphaned', sql: 'SELECT COUNT(*) FROM analytics_events a LEFT JOIN profiles p ON a.user_id = p.id WHERE a.is_demo = true AND p.id IS NULL AND a.user_id IS NOT NULL' },
    { name: 'invalid statuses', sql: "SELECT COUNT(*) FROM orders WHERE is_demo = true AND status NOT IN ('pending', 'accepted', 'preparing', 'ready', 'in_transit', 'completed', 'cancelled', 'requested', 'placed', 'created', 'merchant_accepted', 'arrived', 'started', 'picked_up')" }
  ];

  let failures = 0;
  for (const rule of rules) {
    try {
      const { rows } = await client.query(rule.sql);
      const count = parseInt(rows[0].count, 10);
      if (count > 0) {
        console.error(`❌ FAILED: ${rule.name} -> Found ${count} anomalous rows.`);
        failures++;
      } else {
        console.log(`✅ PASSED: ${rule.name}`);
      }
    } catch (e: any) {
      console.error(`❌ CRASH: ${rule.name} -> ${e.message}`);
      failures++;
    }
  }

  await client.end();
  
  if (failures > 0) {
    console.error(`\n❌ Integrity Audit Failed: ${failures} constraints violated.`);
    process.exit(1);
  }
  console.log('\n✅ Database Integrity Validated.');
}

checkDataIntegrity().catch(console.error);
