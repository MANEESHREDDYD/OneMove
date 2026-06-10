import { test, expect } from '@playwright/test'
import { DEMO_ACCOUNTS, getAnonClient, getUserIdByEmail } from './helpers/finalAuditHelpers'

test.describe('Final security isolation audit', () => {
  test('RLS blocks anonymous and cross-role reads while allowing admin operations', async () => {
    const anon = getAnonClient()
    const { data: anonOrders, error: anonOrdersError } = await anon.from('orders').select('id').limit(5)
    expect(anonOrdersError).toBeNull()
    expect(anonOrders).toEqual([])

    const customer = getAnonClient()
    await customer.auth.signInWithPassword({
      email: DEMO_ACCOUNTS.customer.email,
      password: DEMO_ACCOUNTS.customer.password,
    })
    const customerId = await getUserIdByEmail(DEMO_ACCOUNTS.customer.email)
    const { data: customerOrders, error: customerError } = await customer
      .from('orders')
      .select('id, customer_id')
    expect(customerError).toBeNull()
    expect((customerOrders || []).every((order) => order.customer_id === customerId)).toBe(true)

    const merchant = getAnonClient()
    await merchant.auth.signInWithPassword({
      email: DEMO_ACCOUNTS.merchant.email,
      password: DEMO_ACCOUNTS.merchant.password,
    })
    const merchantOwnerId = await getUserIdByEmail(DEMO_ACCOUNTS.merchant.email)
    const { data: stores } = await merchant.from('merchants').select('id').eq('owner_id', merchantOwnerId)
    const storeIds = new Set((stores || []).map((store) => store.id))
    const { data: merchantOrders, error: merchantError } = await merchant
      .from('orders')
      .select('id, merchant_id')
      .not('merchant_id', 'is', null)
    expect(merchantError).toBeNull()
    expect((merchantOrders || []).every((order) => storeIds.has(order.merchant_id))).toBe(true)

    const partner = getAnonClient()
    await partner.auth.signInWithPassword({
      email: DEMO_ACCOUNTS.partner.email,
      password: DEMO_ACCOUNTS.partner.password,
    })
    const partnerId = await getUserIdByEmail(DEMO_ACCOUNTS.partner.email)
    const { data: partnerOrders, error: partnerError } = await partner
      .from('orders')
      .select('id, driver_id')
    expect(partnerError).toBeNull()
    expect((partnerOrders || []).every((order) => !order.driver_id || order.driver_id === partnerId)).toBe(true)

    const safeCards = getAnonClient()
    await safeCards.auth.signInWithPassword({
      email: DEMO_ACCOUNTS.customer.email,
      password: DEMO_ACCOUNTS.customer.password,
    })
    const { data: cards, error: cardsError } = await safeCards.from('safe_profile_cards').select('*').limit(5)
    expect(cardsError).toBeNull()
    expect(cards && cards.length).toBeGreaterThan(0)
    expect(Object.keys(cards?.[0] || {})).not.toContain('email')
    expect(Object.keys(cards?.[0] || {})).not.toContain('phone')

    const admin = getAnonClient()
    await admin.auth.signInWithPassword({
      email: DEMO_ACCOUNTS.admin.email,
      password: DEMO_ACCOUNTS.admin.password,
    })
    const { count: adminOrderCount, error: adminError } = await admin
      .from('orders')
      .select('*', { count: 'exact', head: true })
    expect(adminError).toBeNull()
    expect(adminOrderCount || 0).toBeGreaterThan(0)
  })
})
