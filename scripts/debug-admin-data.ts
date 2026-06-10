 
import { Client } from 'pg';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

async function checkAdminData() {
  const client = new Client({ connectionString: process.env.DIRECT_URL });
  await client.connect();

  console.log('======================================================================');
  console.log('DEBUG: ADMIN DATA ACCESS & COMMAND CENTER');
  console.log('======================================================================');

  // Verify Admin Profiles exist
  const { rows: admins } = await client.query(`SELECT id, email FROM auth.users WHERE email LIKE 'admin%@onemove.demo'`);
  if (admins.length === 0) {
    console.error('❌ CRITICAL: No admin users found. Command center will be locked out.');
    process.exit(1);
  }
  console.log(`✅ Found ${admins.length} Admin users.`);

  // Assert Command Center macro-queries work properly
  const queries = {
    pendingOrders: "SELECT COUNT(*) FROM orders WHERE status = 'pending'",
    activeOrders: "SELECT COUNT(*) FROM orders WHERE status IN ('accepted', 'preparing', 'ready', 'in_transit')",
    totalUsers: "SELECT COUNT(*) FROM profiles",
    totalMerchants: "SELECT COUNT(*) FROM merchants",
    totalPartners: "SELECT COUNT(*) FROM vehicles",
    anomalousOrders: "SELECT COUNT(*) FROM orders WHERE total_amount = 0",
    stalePayments: "SELECT COUNT(*) FROM payments WHERE status = 'pending_demo' AND created_at < NOW() - INTERVAL '1 day'"
  };

  let failures = 0;
  for (const [key, sql] of Object.entries(queries)) {
    try {
      const { rows } = await client.query(sql);
      const count = parseInt(rows[0].count, 10);
      console.log(`✅ ${key.padEnd(20)} : ${count}`);
    } catch (e: any) {
      console.error(`❌ ${key.padEnd(20)} : FAILED -> ${e.message}`);
      failures++;
    }
  }

  await client.end();
  
  if (failures > 0) {
    console.error(`\n❌ Validation Failed: ${failures} queries crashed. Fix schema alignment.`);
    process.exit(1);
  }
  console.log('\n✅ Admin data queries validated.');
}

checkAdminData().catch(console.error);
