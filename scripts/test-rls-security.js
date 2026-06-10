/**
 * Deep multi-tenant RLS security tests.
 *
 * Simulates each role against Postgres (via DIRECT_URL) by setting the
 * `authenticated`/`anon` role and a JWT claim, exactly as Supabase does, then
 * asserts cross-tenant isolation. Requires service-role + DIRECT_URL in .env.local.
 *
 * Exit code 0 = all checks pass.
 */
const { Client } = require('pg');
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.local' });

const connectionString = process.env.DIRECT_URL;
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!connectionString || !supabaseUrl || !serviceRoleKey) {
  console.error('Missing DB credentials for RLS testing.');
  process.exit(1);
}

const adminClient = createClient(supabaseUrl, serviceRoleKey);
let failed = 0;
const pass = (m) => console.log(`✅ [PASS] ${m}`);
const fail = (m) => { console.log(`❌ [FAIL] ${m}`); failed++; };

async function main() {
  console.log('Running Deep Multi-Tenant RLS Tests...\n');

  // --- Pick representative users per role ---
  const { data: profiles, error } = await adminClient.from('profiles').select('id, role');
  if (error) throw new Error('Failed to list profiles: ' + error.message);

  const customerId = profiles.find((u) => u.role === 'customer')?.id;
  const adminId = profiles.find((u) => u.role === 'admin')?.id;
  const partnerId = profiles.find((u) => u.role === 'driver')?.id;

  // Pick a merchant that actually owns a store WITH orders (so "can read own" is meaningful).
  const { data: stores } = await adminClient.from('merchants').select('id, owner_id');
  const { data: orderRows } = await adminClient.from('orders').select('merchant_id').not('merchant_id', 'is', null);
  const storesWithOrders = new Set((orderRows || []).map((o) => o.merchant_id));
  const ownerToStores = {};
  for (const s of stores || []) {
    (ownerToStores[s.owner_id] ||= []).push(s.id);
  }
  let merchantId = null;
  let merchantStoreIds = new Set();
  for (const [owner, ids] of Object.entries(ownerToStores)) {
    if (ids.some((id) => storesWithOrders.has(id))) {
      merchantId = owner;
      merchantStoreIds = new Set(ids);
      break;
    }
  }

  if (!customerId || !merchantId || !adminId || !partnerId) {
    throw new Error('Demo users (customer/merchant/admin/driver) missing from DB.');
  }

  const client = new Client({ connectionString });
  await client.connect();

  // Run a query as a given authenticated user (or anonymous if uid is null).
  async function queryAs(uid, query) {
    await client.query('BEGIN;');
    if (uid) {
      await client.query('SET LOCAL role TO authenticated;');
      await client.query(`SET LOCAL request.jwt.claims TO '{"role":"authenticated","sub":"${uid}"}';`);
    } else {
      await client.query('SET LOCAL role TO anon;');
      await client.query(`SET LOCAL request.jwt.claims TO '{"role":"anon"}';`);
    }
    const res = await client.query(query);
    await client.query('ROLLBACK;');
    return res.rows;
  }

  try {
    // 1. PROFILES — customer sees only own; safe view exposes display-only.
    const custProfiles = await queryAs(customerId, 'SELECT id FROM profiles;');
    if (custProfiles.length === 1 && custProfiles[0].id === customerId) pass('Customer can read only their own profile.');
    else fail(`Customer can read ${custProfiles.length} profiles (expected 1 = own).`);

    const cardCols = await client.query(
      "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='safe_profile_cards';"
    );
    const colNames = cardCols.rows.map((r) => r.column_name);
    if (!colNames.includes('phone') && !colNames.includes('email')) pass('safe_profile_cards exposes no phone/email.');
    else fail('safe_profile_cards exposes sensitive columns: ' + colNames.join(','));

    const custCards = await queryAs(customerId, 'SELECT id FROM safe_profile_cards LIMIT 5;');
    if (custCards.length > 0) pass('Customer can read display names via safe_profile_cards (no PII).');
    else fail('safe_profile_cards not readable by customer (would break driver name display).');

    // 2. CUSTOMER orders — only own.
    const custOrders = await queryAs(customerId, 'SELECT id, customer_id FROM orders;');
    const crossCustomer = custOrders.filter((o) => o.customer_id !== customerId);
    if (crossCustomer.length === 0) pass('Customer can read only their own orders.');
    else fail(`Customer can read ${crossCustomer.length} orders that are not theirs.`);

    // 3. MERCHANT orders — own store(s) only (tenancy by merchants.owner_id).
    const merchOrders = await queryAs(merchantId, 'SELECT id, merchant_id FROM orders;');
    const ownMerch = merchOrders.filter((o) => merchantStoreIds.has(o.merchant_id));
    const crossMerch = merchOrders.filter((o) => o.merchant_id && !merchantStoreIds.has(o.merchant_id));
    if (ownMerch.length > 0) pass(`Merchant can read their own orders (${ownMerch.length}).`);
    else fail('Merchant cannot read their own orders.');
    if (crossMerch.length === 0) pass('Merchant cannot read other merchants\' orders.');
    else fail(`Merchant can read ${crossMerch.length} orders from OTHER merchants (cross-tenant leak).`);

    // 4. MERCHANT order_items / payments — scoped to own orders only.
    const merchItems = await queryAs(
      merchantId,
      'SELECT oi.order_id, o.merchant_id FROM order_items oi JOIN orders o ON o.id = oi.order_id;'
    );
    const crossItems = merchItems.filter((r) => r.merchant_id && !merchantStoreIds.has(r.merchant_id));
    if (crossItems.length === 0) pass('Merchant order_items are scoped to own orders.');
    else fail(`Merchant can read order_items for ${crossItems.length} other-merchant orders.`);

    const merchPayments = await queryAs(
      merchantId,
      'SELECT p.order_id, o.merchant_id FROM payments p JOIN orders o ON o.id = p.order_id;'
    );
    const crossPay = merchPayments.filter((r) => r.merchant_id && !merchantStoreIds.has(r.merchant_id));
    if (crossPay.length === 0) pass('Merchant payments are scoped to own orders only.');
    else fail(`Merchant can read payments for ${crossPay.length} other-merchant orders.`);

    // 5. PARTNER orders — assigned to self or unassigned/available only.
    const partnerOrders = await queryAs(partnerId, 'SELECT id, driver_id FROM orders;');
    const otherDriver = partnerOrders.filter((o) => o.driver_id && o.driver_id !== partnerId);
    if (otherDriver.length === 0) pass('Partner sees only assigned/available jobs (no other-driver jobs).');
    else fail(`Partner can read ${otherDriver.length} jobs assigned to OTHER drivers.`);

    // 6. CUSTOMER cannot read admin operational tables.
    const custInsights = await queryAs(customerId, 'SELECT id FROM ops_insights;');
    if (custInsights.length === 0) pass('Customer cannot read ops_insights.');
    else fail('Customer can read ops_insights.');
    const custMl = await queryAs(customerId, 'SELECT id FROM ml_pipeline_runs;');
    if (custMl.length === 0) pass('Customer cannot read ml_pipeline_runs.');
    else fail('Customer can read ml_pipeline_runs.');

    // 7. ADMIN can read platform-wide operational data.
    const adminOrders = await queryAs(adminId, 'SELECT count(*)::int n FROM orders;');
    const totalOrders = (await adminClient.from('orders').select('*', { count: 'exact', head: true })).count || 0;
    if (adminOrders[0].n >= totalOrders && totalOrders > 0) pass(`Admin can read all ${adminOrders[0].n} orders.`);
    else fail(`Admin sees ${adminOrders[0].n} of ${totalOrders} orders.`);
    const adminInsights = await queryAs(adminId, 'SELECT id FROM ops_insights;');
    if (adminInsights.length > 0) pass('Admin can read ops_insights.');
    else fail('Admin cannot read ops_insights.');

    // 8. ANONYMOUS cannot read protected operational data.
    const anonOrders = await queryAs(null, 'SELECT id FROM orders;');
    if (anonOrders.length === 0) pass('Anonymous cannot read orders.');
    else fail(`Anonymous can read ${anonOrders.length} orders.`);
    const anonProfiles = await queryAs(null, 'SELECT id FROM profiles;');
    if (anonProfiles.length === 0) pass('Anonymous cannot read profiles.');
    else fail(`Anonymous can read ${anonProfiles.length} profiles.`);
    const anonPayments = await queryAs(null, 'SELECT id FROM payments;');
    if (anonPayments.length === 0) pass('Anonymous cannot read payments.');
    else fail(`Anonymous can read ${anonPayments.length} payments.`);
  } finally {
    await client.end();
  }

  console.log(`\nRLS QA Results: ${failed === 0 ? 'ALL PASSED' : failed + ' Failed'}`);
  process.exitCode = failed === 0 ? 0 : 1;
}

main().catch((e) => {
  console.error('RLS test error:', e.message);
  process.exitCode = 1;
});
