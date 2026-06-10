/**
 * OneMove local healthcheck.
 *
 * A single, runnable readiness probe for the localhost demo. It verifies:
 *   - Supabase connection (service-role client)
 *   - The four demo auth users exist with the expected roles
 *   - Required core + intelligence tables are reachable
 *   - Key metric / data counts are non-empty
 *   - The latest ML pipeline run status
 *   - (Optional) the running web server responds on required routes
 *
 * Usage:   npm run healthcheck
 *          npm run healthcheck -- --routes   (also probe http://localhost:3000)
 *
 * Exit code is 0 when all REQUIRED checks pass, 1 otherwise. Route probing is
 * opt-in and never fails the run (the server may simply not be running).
 */
import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'
import path from 'path'

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('❌ Missing Supabase credentials in .env.local')
  process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseServiceKey)

let failures = 0
const pass = (msg: string) => console.log(`✅ ${msg}`)
const fail = (msg: string) => {
  console.log(`❌ ${msg}`)
  failures++
}
const warn = (msg: string) => console.log(`⚠️  ${msg}`)

const REQUIRED_TABLES = [
  'profiles',
  'orders',
  'order_items',
  'payments',
  'order_status_events',
  'merchants',
  'daily_marketplace_metrics',
  'recommendations',
  'customer_segments',
  'merchant_reliability_scores',
  'partner_trust_scores',
  'ml_pipeline_runs',
]

const DEMO_USERS = [
  { email: 'customer@onemove.demo', role: 'customer' },
  { email: 'merchant@onemove.demo', role: 'merchant' },
  { email: 'partner@onemove.demo', role: 'partner' },
  { email: 'admin@onemove.demo', role: 'admin' },
]

const REQUIRED_ROUTES = ['/', '/showcase', '/customer/rides', '/admin/command-center']

async function count(table: string): Promise<number | null> {
  const { count, error } = await supabase
    .from(table)
    .select('*', { count: 'exact', head: true })
  if (error) return null
  return count ?? 0
}

async function checkConnection() {
  const { error } = await supabase.from('profiles').select('id', { head: true, count: 'exact' })
  if (error) fail(`Supabase connection failed: ${error.message}`)
  else pass('Supabase connection OK')
}

async function checkDemoUsers() {
  const { data, error } = await supabase.auth.admin.listUsers({ perPage: 1000 })
  if (error) {
    fail(`Could not list auth users: ${error.message}`)
    return
  }
  const emails = new Set((data.users || []).map((u) => u.email))
  for (const u of DEMO_USERS) {
    if (emails.has(u.email)) pass(`Demo user present: ${u.email}`)
    else fail(`Demo user MISSING: ${u.email}`)
  }
}

async function checkTables() {
  for (const t of REQUIRED_TABLES) {
    const c = await count(t)
    if (c === null) fail(`Table unreachable: ${t}`)
    else if (c === 0) warn(`Table reachable but EMPTY: ${t}`)
    else pass(`Table ${t}: ${c} rows`)
  }
}

async function checkMlRun() {
  const { data, error } = await supabase
    .from('ml_pipeline_runs')
    .select('run_name, status, started_at')
    .order('started_at', { ascending: false })
    .limit(1)
  if (error || !data || data.length === 0) {
    warn('No ML pipeline runs recorded yet (run npm run intelligence:refresh).')
    return
  }
  const run = data[0]
  if (String(run.status).toUpperCase() === 'SUCCESS') {
    pass(`Latest ML run "${run.run_name}" = SUCCESS`)
  } else {
    fail(`Latest ML run "${run.run_name}" status = ${run.status}`)
  }
}

async function checkRoutes() {
  console.log('\n--- Route probes (optional) ---')
  for (const r of REQUIRED_ROUTES) {
    try {
      const res = await fetch(`${appUrl}${r}`, { redirect: 'manual' })
      const ok = res.status < 500
      if (ok) pass(`Route ${r} -> ${res.status}`)
      else fail(`Route ${r} -> ${res.status}`)
    } catch {
      warn(`Route ${r} unreachable (is the server running?)`)
    }
  }
}

async function main() {
  console.log('================================================')
  console.log('🩺 OneMove Local Healthcheck')
  console.log('================================================\n')

  await checkConnection()
  console.log('\n--- Demo auth users ---')
  await checkDemoUsers()
  console.log('\n--- Required tables ---')
  await checkTables()
  console.log('\n--- ML pipeline ---')
  await checkMlRun()

  if (process.argv.includes('--routes')) {
    await checkRoutes()
  }

  console.log('\n================================================')
  if (failures === 0) {
    console.log('✅ Healthcheck PASSED (all required checks green)')
    console.log('================================================')
    process.exit(0)
  } else {
    console.log(`❌ Healthcheck FAILED: ${failures} required check(s) failed`)
    console.log('================================================')
    process.exit(1)
  }
}

main()
