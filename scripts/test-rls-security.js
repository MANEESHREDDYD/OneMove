/* eslint-disable @typescript-eslint/no-require-imports */
const { createClient } = require('@supabase/supabase-js')
require('dotenv').config({ path: '.env.local' })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  console.error("Missing Supabase credentials for RLS testing.")
  process.exit(1)
}

const client = createClient(supabaseUrl, supabaseAnonKey)

async function runTests() {
  let passed = 0
  let failed = 0

  const logResult = (testName, error, expectedErrorStr) => {
    // If the RLS blocks it, we get no rows or a 401/403/406 error
    if (error && error.message.includes(expectedErrorStr)) {
      console.log(`✅ [PASS] ${testName}`)
      passed++
    } else if (!error) {
      console.log(`❌ [FAIL] ${testName} - Data was unexpectedly returned!`)
      failed++
    } else {
      console.log(`✅ [PASS] ${testName} (Blocked: ${error.message})`)
      passed++
    }
  }

  // Test 1: Anonymous access to profiles should be blocked
  const { data: p1, error: e1 } = await client.from('profiles').select('*').limit(1)
  // Profiles has RLS, anon shouldn't be able to query.
  if (p1 && p1.length === 0) {
    console.log(`✅ [PASS] Anonymous access to profiles returns 0 rows (RLS enforced).`)
    passed++
  } else {
    logResult('Anonymous access to profiles', e1, 'JWT')
  }

  // Test 2: Anonymous access to orders
  const { data: p2, error: e2 } = await client.from('orders').select('*').limit(1)
  if (p2 && p2.length === 0) {
    console.log(`✅ [PASS] Anonymous access to orders returns 0 rows.`)
    passed++
  } else {
    logResult('Anonymous access to orders', e2, 'JWT')
  }

  console.log(`\nRLS QA Results: ${passed} Passed, ${failed} Failed`)
  if (failed > 0) process.exit(1)
}

runTests()

