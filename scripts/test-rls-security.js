/* eslint-disable @typescript-eslint/no-require-imports */
const { Client } = require('pg');
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.local' });

const connectionString = process.env.DIRECT_URL;
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!connectionString || !supabaseUrl || !serviceRoleKey) {
  console.error("Missing DB credentials for RLS testing.");
  process.exit(1);
}

const adminClient = createClient(supabaseUrl, serviceRoleKey);

async function runTests() {
  console.log("Running Deep Multi-Tenant RLS Tests...\n");
  let failed = 0;

  const logPass = (msg) => console.log(`✅ [PASS] ${msg}`);
  const logFail = (msg) => { console.log(`❌ [FAIL] ${msg}`); failed++; };

  // 1. Get user IDs
  const { data: { users }, error } = await adminClient.auth.admin.listUsers();
  if (error) { logFail("Failed to list users"); process.exit(1); }

  const customerId = users.find(u => u.email === 'customer@onemove.demo')?.id;
  const merchantId = users.find(u => u.email === 'merchant@onemove.demo')?.id;
  const adminId = users.find(u => u.email === 'admin@onemove.demo')?.id;

  if (!customerId || !merchantId || !adminId) {
    logFail("Demo users missing from DB.");
    process.exit(1);
  }

  const client = new Client({ connectionString });
  await client.connect();

  async function queryAsUser(userId, query) {
    await client.query("BEGIN;");
    await client.query(`SET LOCAL role TO authenticated;`);
    // Mock the JWT payload
    await client.query(`SET LOCAL request.jwt.claims TO '{"role":"authenticated", "sub":"${userId}"}';`);
    const res = await client.query(query);
    await client.query("ROLLBACK;");
    return res.rows;
  }

  // 2. Customer A vs Profiles
  const custProfiles = await queryAsUser(customerId, "SELECT id FROM profiles;");
  if (custProfiles.length === 1 && custProfiles[0].id === customerId) {
    logPass("Customer can only read their own profile.");
  } else {
    logFail(`Customer can read ${custProfiles.length} profiles (Expected 1).`);
  }

  // 3. Customer A vs Customer B Orders
  const custOrders = await queryAsUser(customerId, "SELECT id, customer_id FROM orders;");
  const crossCustomer = custOrders.filter(o => o.customer_id !== customerId);
  if (crossCustomer.length === 0) {
    logPass("Customer cannot read other customers' orders.");
  } else {
    logFail("Customer can read other orders.");
  }

  // 4. Merchant vs Merchant Orders
  const merchOrders = await queryAsUser(merchantId, "SELECT id, merchant_id FROM orders;");
  const crossMerchant = merchOrders.filter(o => o.merchant_id !== merchantId);
  if (crossMerchant.length === 0) {
    logPass("Merchant cannot read other merchants' orders.");
  } else {
    logFail("Merchant can read other merchants' orders.");
  }

  // 5. Customer vs Global Merchants
  const stores = await queryAsUser(customerId, "SELECT id FROM merchants;");
  if (stores.length === 0) {
    logPass("Customer cannot read raw merchants table directly.");
  } else {
    logFail("Customer can read raw merchants table.");
  }

  console.log(`\nRLS QA Results: ${failed === 0 ? "All Passed" : failed + " Failed"}`);
  await client.end();
  if (failed > 0) process.exit(1);
}

runTests();
