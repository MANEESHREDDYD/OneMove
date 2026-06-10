/* eslint-disable @typescript-eslint/no-require-imports */
const { chromium } = require('@playwright/test')
const { createClient } = require('@supabase/supabase-js')
const dotenv = require('dotenv')

dotenv.config({ path: '.env.local' })

const BASE_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

const ACCOUNTS = {
  customer: { email: 'customer@onemove.demo', password: 'Demo@12345' },
  merchant: { email: 'merchant@onemove.demo', password: 'Demo@12345' },
  partner: { email: 'partner@onemove.demo', password: 'Demo@12345' },
  admin: { email: 'admin@onemove.demo', password: 'Demo@12345' },
}

function requireEnv(name) {
  const value = process.env[name]
  if (!value) throw new Error(`Missing ${name}`)
  return value
}

async function latestCustomerOrderPath() {
  const supabase = createClient(
    requireEnv('NEXT_PUBLIC_SUPABASE_URL'),
    requireEnv('SUPABASE_SERVICE_ROLE_KEY'),
    { auth: { autoRefreshToken: false, persistSession: false } }
  )

  const { data: users, error: usersError } = await supabase.auth.admin.listUsers({
    page: 1,
    perPage: 1000,
  })
  if (usersError) throw usersError

  const customer = users.users.find((user) => user.email === ACCOUNTS.customer.email)
  if (!customer) throw new Error('Missing primary demo customer')

  const { data: order, error } = await supabase
    .from('orders')
    .select('id')
    .eq('customer_id', customer.id)
    .order('created_at', { ascending: false })
    .limit(1)
    .single()
  if (error) throw error

  return `/customer/orders/${order.id}`
}

async function login(page, role) {
  const account = ACCOUNTS[role]
  await page.goto(`${BASE_URL}/auth/login`, { waitUntil: 'domcontentloaded' })
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await page.waitForURL(new RegExp(`/${role === 'partner' ? 'partner' : role}`), {
    timeout: 20000,
  })
}

async function measure(page, path) {
  const started = Date.now()
  const response = await page.goto(`${BASE_URL}${path}`, { waitUntil: 'domcontentloaded' })
  const elapsedMs = Date.now() - started
  const status = response ? response.status() : 0
  const bodyText = await page.locator('body').innerText()

  return {
    path,
    status,
    elapsedMs,
    bodyChars: bodyText.trim().length,
  }
}

async function run() {
  const customerOrderPath = await latestCustomerOrderPath()
  const scenarios = [
    { role: 'admin', path: '/admin/command-center' },
    { role: 'customer', path: '/customer/rides' },
    { role: 'customer', path: customerOrderPath },
    { role: 'merchant', path: '/merchant/orders' },
    { role: 'partner', path: '/partner/jobs' },
    { role: 'admin', path: '/admin/system-health' },
  ]

  const browser = await chromium.launch()
  const results = []
  const failures = []

  for (const scenario of scenarios) {
    const context = await browser.newContext()
    const page = await context.newPage()
    await login(page, scenario.role)

    for (let i = 0; i < 3; i += 1) {
      const result = await measure(page, scenario.path)
      results.push({ ...scenario, iteration: i + 1, ...result })
      if (result.status >= 500 || result.bodyChars < 20) {
        failures.push(result)
      }
    }

    await context.close()
  }

  await browser.close()

  console.table(
    results.map((result) => ({
      role: result.role,
      path: result.path,
      iteration: result.iteration,
      status: result.status,
      elapsedMs: result.elapsedMs,
      bodyChars: result.bodyChars,
    }))
  )

  const maxMs = Math.max(...results.map((result) => result.elapsedMs))
  const avgMs = Math.round(
    results.reduce((sum, result) => sum + result.elapsedMs, 0) / results.length
  )
  console.log(`Local performance smoke summary: avg=${avgMs}ms max=${maxMs}ms samples=${results.length}`)

  if (failures.length > 0) {
    console.error(`Performance smoke failed: ${failures.length} bad response(s).`)
    process.exit(1)
  }
}

run().catch((error) => {
  console.error(error)
  process.exit(1)
})
