import { Client } from 'pg';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const directUrl = process.env.DIRECT_URL;
if (!directUrl) {
  console.error("Missing DIRECT_URL");
  process.exit(1);
}

const pgClient = new Client({ connectionString: directUrl });

async function debugRoleData() {
  await pgClient.connect();
  console.log("========================================");
  console.log("ROLE DATA MAPPING DEBUG REPORT");
  console.log("========================================\n");

  // 1. Merchant Debug
  console.log("--- MERCHANT DEBUG ---");
  for (const email of ['merchant@onemove.demo', 'merchant001@onemove.demo']) {
    console.log(`\nEmail: ${email}`);
    const { rows: uRows } = await pgClient.query(`SELECT id FROM auth.users WHERE email = $1`, [email]);
    if (uRows.length === 0) {
      console.log("❌ Auth User Not Found");
      continue;
    }
    const authId = uRows[0].id;
    console.log(`Auth ID: ${authId}`);

    const { rows: pRows } = await pgClient.query(`SELECT id, role FROM profiles WHERE id = $1`, [authId]);
    console.log(`Profile ID: ${pRows.length ? pRows[0].id : 'MISSING'} (Role: ${pRows.length ? pRows[0].role : 'N/A'})`);

    const { rows: mRows } = await pgClient.query(`SELECT id, name FROM merchants WHERE owner_id = $1`, [authId]);
    if (mRows.length === 0) {
      console.log("❌ Merchant Record: MISSING");
      continue;
    }
    const merchantIds = mRows.map(m => m.id);
    console.log(`Merchant ID(s): ${merchantIds.join(', ')}`);

    // Check orders for this merchant
    const { rows: oRows } = await pgClient.query(`
      SELECT 
        COUNT(*) as total_orders,
        COUNT(CASE WHEN status IN ('pending', 'accepted', 'preparing', 'ready') THEN 1 END) as active_orders,
        SUM(total_amount) as revenue
      FROM orders 
      WHERE merchant_id = ANY($1)
    `, [merchantIds]);
    
    console.log(`Total Orders: ${oRows[0].total_orders}`);
    console.log(`Active Orders: ${oRows[0].active_orders}`);
    console.log(`Revenue: $${oRows[0].revenue || '0.00'}`);
  }

  // 2. Partner Debug
  console.log("\n--- PARTNER DEBUG ---");
  for (const email of ['partner@onemove.demo', 'partner001@onemove.demo']) {
    console.log(`\nEmail: ${email}`);
    const { rows: uRows } = await pgClient.query(`SELECT id FROM auth.users WHERE email = $1`, [email]);
    if (uRows.length === 0) {
      console.log("❌ Auth User Not Found");
      continue;
    }
    const authId = uRows[0].id;
    console.log(`Auth ID: ${authId}`);

    const { rows: pRows } = await pgClient.query(`SELECT id, role FROM profiles WHERE id = $1`, [authId]);
    console.log(`Profile ID: ${pRows.length ? pRows[0].id : 'MISSING'} (Role: ${pRows.length ? pRows[0].role : 'N/A'})`);

    // Partner Jobs queries
    const { rows: assignedRows } = await pgClient.query(`
      SELECT COUNT(*) as count FROM orders 
      WHERE driver_id = $1 AND status IN ('accepted', 'in_transit', 'preparing', 'ready')
    `, [authId]);
    
    const { rows: completedRows } = await pgClient.query(`
      SELECT COUNT(*) as count FROM orders 
      WHERE driver_id = $1 AND status IN ('completed')
    `, [authId]);

    const { rows: availableRows } = await pgClient.query(`
      SELECT COUNT(*) as count FROM orders 
      WHERE (driver_id IS NULL OR driver_id = $1) 
      AND status IN ('pending', 'ready')
    `, [authId]);

    const { rows: earningsRows } = await pgClient.query(`
      SELECT SUM(amount) as total FROM payments 
      WHERE order_id IN (SELECT id FROM orders WHERE driver_id = $1)
    `, [authId]); // rough estimate of earnings mapping

    console.log(`Assigned Jobs: ${assignedRows[0].count}`);
    console.log(`Available Jobs: ${availableRows[0].count}`);
    console.log(`Completed Jobs: ${completedRows[0].count}`);
    console.log(`Earnings: $${earningsRows[0].total || '0.00'}`);
  }

  // 3. Customer Debug
  console.log("\n--- CUSTOMER DEBUG ---");
  for (const email of ['customer@onemove.demo', 'customer001@onemove.demo']) {
    console.log(`\nEmail: ${email}`);
    const { rows: uRows } = await pgClient.query(`SELECT id FROM auth.users WHERE email = $1`, [email]);
    if (uRows.length === 0) {
      console.log("❌ Auth User Not Found");
      continue;
    }
    const authId = uRows[0].id;
    console.log(`Auth ID: ${authId}`);

    const { rows: pRows } = await pgClient.query(`SELECT id, role FROM profiles WHERE id = $1`, [authId]);
    console.log(`Profile ID: ${pRows.length ? pRows[0].id : 'MISSING'} (Role: ${pRows.length ? pRows[0].role : 'N/A'})`);

    const { rows: oRows } = await pgClient.query(`
      SELECT 
        COUNT(*) as total_orders,
        COUNT(CASE WHEN service_type = 'ride' THEN 1 END) as rides,
        COUNT(CASE WHEN service_type = 'courier' THEN 1 END) as courier_jobs
      FROM orders WHERE customer_id = $1
    `, [authId]);

    console.log(`Total Orders: ${oRows[0].total_orders}`);
    console.log(`Rides: ${oRows[0].rides}`);
    console.log(`Courier Jobs: ${oRows[0].courier_jobs}`);
  }

  console.log("\n========================================");
  await pgClient.end();
}

debugRoleData().catch(e => {
  console.error(e);
  process.exit(1);
});
