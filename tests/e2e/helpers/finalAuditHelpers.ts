import { expect, type Page } from '@playwright/test'
import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'

dotenv.config({ path: '.env.local' })

export const DEMO_ACCOUNTS = {
  customer: { email: 'customer@onemove.demo', password: 'Demo@12345', route: /\/customer/ },
  merchant: { email: 'merchant@onemove.demo', password: 'Demo@12345', route: /\/merchant/ },
  partner: { email: 'partner@onemove.demo', password: 'Demo@12345', route: /\/partner/ },
  admin: { email: 'admin@onemove.demo', password: 'Demo@12345', route: /\/admin\/command-center/ },
} as const

const fatalPatterns = [
  /hydration/i,
  /_leaflet_pos/i,
  /window is not defined/i,
  /uncaught/i,
  /500 internal server error/i,
]

export function attachStrictAudit(page: Page) {
  const issues: string[] = []

  page.on('console', (msg) => {
    const text = msg.text()
    if (msg.type() === 'error') {
      issues.push(`console.error: ${text}`)
      return
    }
    if (fatalPatterns.some((pattern) => pattern.test(text))) {
      issues.push(`fatal console pattern: ${text}`)
    }
  })

  page.on('pageerror', (error) => {
    issues.push(`uncaught exception: ${error.message}`)
  })

  page.on('requestfailed', (request) => {
    const failure = request.failure()?.errorText || ''
    if (failure.includes('ERR_ABORTED')) return
    if (request.url().includes('favicon.ico')) return
    issues.push(`request failed: ${request.url()} ${failure}`)
  })

  page.on('response', (response) => {
    if (response.status() >= 500) {
      issues.push(`server ${response.status()}: ${response.url()}`)
    }
  })

  return async () => {
    await page.waitForTimeout(250)
    expect(issues, issues.join('\n')).toEqual([])
  }
}

export async function loginAs(page: Page, role: keyof typeof DEMO_ACCOUNTS) {
  const account = DEMO_ACCOUNTS[role]
  await page.goto('/auth/login')
  await page.getByLabel('Email').fill(account.email)
  await page.getByLabel('Password').fill(account.password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(account.route, { timeout: 15000 })
}

export async function assertUsablePage(page: Page, path: string) {
  await page.goto(path)
  await page.waitForLoadState('domcontentloaded')
  await expect(page.locator('body')).not.toContainText('500 Internal Server Error')
  await expect(page.locator('body')).not.toContainText('Application error')
  const textLength = await page.locator('body').innerText().then((text) => text.trim().length)
  expect(textLength, `${path} should not be blank`).toBeGreaterThan(20)
}

export async function signOut(page: Page) {
  const signOutButton = page.getByRole('button', { name: /sign out/i }).first()
  if (!(await signOutButton.isVisible({ timeout: 1000 }).catch(() => false))) {
    const currentPath = new URL(page.url()).pathname
    if (currentPath.startsWith('/admin')) await page.goto('/admin/command-center')
    else if (currentPath.startsWith('/merchant')) await page.goto('/merchant')
    else if (currentPath.startsWith('/partner')) await page.goto('/partner')
    else await page.goto('/customer')
  }

  await page.getByRole('button', { name: /sign out/i }).first().click()
  await expect(page).toHaveURL(/\/auth\/login/, { timeout: 15000 })
}

export function getAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !serviceKey) throw new Error('Missing Supabase service credentials for final audit tests')
  return createClient(url, serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })
}

export function getAnonClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  if (!url || !anonKey) throw new Error('Missing Supabase anon credentials for final audit tests')
  return createClient(url, anonKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  })
}

export async function getUserIdByEmail(email: string) {
  const admin = getAdminClient()
  const { data, error } = await admin.auth.admin.listUsers({ page: 1, perPage: 1000 })
  if (error) throw error
  const user = data.users.find((item) => item.email === email)
  if (!user) throw new Error(`Missing demo user ${email}`)
  return user.id
}

export async function createDemoOrderForMerchant() {
  const admin = getAdminClient()
  const customerId = await getUserIdByEmail(DEMO_ACCOUNTS.customer.email)
  const merchantOwnerId = await getUserIdByEmail(DEMO_ACCOUNTS.merchant.email)
  const partnerId = await getUserIdByEmail(DEMO_ACCOUNTS.partner.email)

  const { data: merchant, error: merchantError } = await admin
    .from('merchants')
    .select('id, name')
    .eq('owner_id', merchantOwnerId)
    .limit(1)
    .single()
  if (merchantError) throw merchantError

  const { data: product, error: productError } = await admin
    .from('products')
    .select('id, price')
    .eq('merchant_id', merchant.id)
    .limit(1)
    .single()
  if (productError) throw productError

  const pickup = { address: merchant.name || 'Demo Merchant', lat: 40.7128, lng: -74.006 }
  const dropoff = { address: 'Final audit customer address', lat: 40.7306, lng: -73.9352 }
  const totalAmount = Number(product.price || 24.5)

  const { data: order, error } = await admin
    .from('orders')
    .insert({
      customer_id: customerId,
      merchant_id: merchant.id,
      driver_id: partnerId,
      service_type: 'eats',
      status: 'pending',
      total_amount: totalAmount,
      pickup_location: pickup,
      dropoff_location: dropoff,
      metadata: { source: 'final-audit-merchant-flow' },
      is_demo: true,
    })
    .select('id')
    .single()
  if (error) throw error

  const [{ error: itemError }, { error: paymentError }, { error: eventError }] = await Promise.all([
    admin.from('order_items').insert({
      order_id: order.id,
      product_id: product.id,
      quantity: 1,
      price_at_time: totalAmount,
      is_demo: true,
    }),
    admin.from('payments').insert({
      order_id: order.id,
      customer_id: customerId,
      amount: totalAmount,
      status: 'paid_demo',
      method: 'demo_wallet',
      is_demo: true,
    }),
    admin.from('order_status_events').insert({
      order_id: order.id,
      status: 'pending',
      notes: `Final audit merchant-flow fixture created by ${customerId}`,
      is_demo: true,
    }),
  ])
  if (itemError) throw itemError
  if (paymentError) throw paymentError
  if (eventError) throw eventError

  return order.id as string
}

export async function createDemoOrderForPartner() {
  const admin = getAdminClient()
  const customerId = await getUserIdByEmail(DEMO_ACCOUNTS.customer.email)

  const { data: order, error } = await admin
    .from('orders')
    .insert({
      customer_id: customerId,
      service_type: 'ride',
      status: 'requested',
      total_amount: 18.75,
      pickup_location: { address: 'Final Audit Pickup', lat: 40.758, lng: -73.9855 },
      dropoff_location: { address: 'Final Audit Dropoff', lat: 40.7061, lng: -74.0086 },
      metadata: { ride_type: 'economy', source: 'final-audit-partner-flow' },
      is_demo: true,
    })
    .select('id')
    .single()
  if (error) throw error

  const [{ error: paymentError }, { error: eventError }] = await Promise.all([
    admin.from('payments').insert({
      order_id: order.id,
      customer_id: customerId,
      amount: 18.75,
      status: 'paid_demo',
      method: 'demo_wallet',
      is_demo: true,
    }),
    admin.from('order_status_events').insert({
      order_id: order.id,
      status: 'requested',
      notes: `Final audit partner-flow fixture created by ${customerId}`,
      is_demo: true,
    }),
  ])
  if (paymentError) throw paymentError
  if (eventError) throw eventError

  return order.id as string
}
