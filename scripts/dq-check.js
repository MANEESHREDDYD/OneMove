/* eslint-disable @typescript-eslint/no-require-imports */
const { createClient } = require('@supabase/supabase-js')
require('dotenv').config({ path: '.env.local' })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!supabaseUrl || !supabaseServiceKey) {
  console.error("Missing credentials for Data Quality Checks.")
  process.exit(1)
}

const client = createClient(supabaseUrl, supabaseServiceKey)

async function runDQ() {
  console.log("Running Data Quality Checks...\n")
  let failures = 0

  // 1. Core tables exist
  const tables = ['profiles', 'merchants', 'orders', 'vehicles']
  for (const t of tables) {
    const { count, error } = await client.from(t).select('*', { count: 'exact', head: true })
    if (error) {
      console.log(`❌ [FAIL] Table ${t} is inaccessible:`, error.message)
      failures++
    } else {
      console.log(`✅ [PASS] Table ${t} exists (Rows: ${count})`)
    }
  }

  // 2. Detect missing merchant/customer references
  const { data: orders, error: ordersErr } = await client.from('orders').select('id, customer_id, merchant_id')
  if (ordersErr) {
    console.log(`❌ [FAIL] Cannot fetch orders for integrity check.`)
    failures++
  } else if (orders.length > 0) {
    let orphans = 0
    orders.forEach(o => {
      if (!o.customer_id && !o.merchant_id) orphans++ // at least one should exist usually
    })
    if (orphans > 0) {
      console.log(`❌ [FAIL] Found ${orphans} orphan orders lacking associations.`)
      failures++
    } else {
      console.log(`✅ [PASS] Order referential associations intact.`)
    }
  }

  // 3. Detect invalid order totals
  const { data: invalidTotals } = await client.from('orders').select('id, total_amount').lt('total_amount', 0)
  if (invalidTotals && invalidTotals.length > 0) {
    console.log(`❌ [FAIL] Found ${invalidTotals.length} orders with negative total_amount.`)
    failures++
  } else {
    console.log(`✅ [PASS] No negative total amounts found in orders.`)
  }

  console.log(`\nDQ Run Complete. Failures: ${failures}`)
  process.exit(failures > 0 ? 1 : 0)
}

runDQ()

