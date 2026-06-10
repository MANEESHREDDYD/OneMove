import { SupabaseClient } from '@supabase/supabase-js'

/**
 * Computes and inserts/upserts daily metrics from the raw `orders` table
 * for a specific targetDate (YYYY-MM-DD).
 */
export async function computeDailyMetrics(supabaseAdmin: SupabaseClient, targetDate: string) {
  // 1. Fetch raw orders for the target date
  // Since timestamps are TIMESTAMPTZ, we'll bound the search between start and end of the day UTC
  const startDate = `${targetDate}T00:00:00Z`
  const endDate = `${targetDate}T23:59:59.999Z`

  const { data: orders, error } = await supabaseAdmin
    .from('orders')
    .select('*')
    .gte('created_at', startDate)
    .lte('created_at', endDate)

  if (error) throw error

  // Calculate Aggregates
  let gmv = 0
  const totalOrders = orders.length
  let completedOrders = 0
  let cancelledOrders = 0
  const refundCount = 0

  const activeCustomers = new Set<string>()
  const activePartners = new Set<string>()
  const activeMerchants = new Set<string>()

  // Merchant, Partner, Customer, and Service Type Aggregations
  const merchantStats: Record<string, { orders: number; completed: number; gmv: number }> = {}
  const partnerStats: Record<string, { completed: number; earnings: number }> = {}
  const customerStats: Record<string, { orders: number; spend: number }> = {}
  const serviceStats: Record<string, { gmv: number; total: number; completed: number }> = {}

  for (const order of orders) {
    const isCompleted = order.status === 'completed' || order.status === 'delivered'
    const isCancelled = order.status === 'cancelled'
    const amount = Number(order.total_amount) || 0

    if (isCompleted) {
      completedOrders++
      gmv += amount
    } else if (isCancelled) {
      cancelledOrders++
    }

    if (order.customer_id) {
      activeCustomers.add(order.customer_id)
      if (!customerStats[order.customer_id]) customerStats[order.customer_id] = { orders: 0, spend: 0 }
      customerStats[order.customer_id].orders++
      if (isCompleted) customerStats[order.customer_id].spend += amount
    }

    if (order.merchant_id && isCompleted) {
      activeMerchants.add(order.merchant_id)
      if (!merchantStats[order.merchant_id]) merchantStats[order.merchant_id] = { orders: 0, completed: 0, gmv: 0 }
      merchantStats[order.merchant_id].orders++
      merchantStats[order.merchant_id].completed++
      merchantStats[order.merchant_id].gmv += amount
    }

    if (order.driver_id && isCompleted) {
      activePartners.add(order.driver_id)
      if (!partnerStats[order.driver_id]) partnerStats[order.driver_id] = { completed: 0, earnings: 0 }
      partnerStats[order.driver_id].completed++
      // Dummy estimation: partners earn 75% of GMV
      partnerStats[order.driver_id].earnings += (amount * 0.75)
    }

    if (order.service_type) {
      if (!serviceStats[order.service_type]) serviceStats[order.service_type] = { gmv: 0, total: 0, completed: 0 }
      serviceStats[order.service_type].total++
      if (isCompleted) {
        serviceStats[order.service_type].completed++
        serviceStats[order.service_type].gmv += amount
      }
    }
  }

  const netRevenue = gmv * 0.20 // 20% platform take rate
  const refundRate = completedOrders > 0 ? (refundCount / completedOrders) * 100 : 0

  // 2. Upsert Global Daily Metrics
  await supabaseAdmin.from('daily_marketplace_metrics').upsert({
    date: targetDate,
    gmv,
    net_revenue: netRevenue,
    total_orders: totalOrders,
    completed_orders: completedOrders,
    cancelled_orders: cancelledOrders,
    refund_rate: refundRate,
    active_customers: activeCustomers.size,
    active_partners: activePartners.size,
    active_merchants: activeMerchants.size,
    updated_at: new Date().toISOString()
  })

  // 3. Upsert Service Type Metrics
  const serviceUpserts = Object.keys(serviceStats).map(st => ({
    date: targetDate,
    service_type: st,
    gmv: serviceStats[st].gmv,
    total_orders: serviceStats[st].total,
    completed_orders: serviceStats[st].completed,
    updated_at: new Date().toISOString()
  }))
  if (serviceUpserts.length) {
    await supabaseAdmin.from('service_type_daily_metrics').upsert(serviceUpserts)
  }

  // 4. Upsert Merchant Metrics
  const merchantUpserts = Object.keys(merchantStats).map(mid => ({
    date: targetDate,
    merchant_id: mid,
    gmv: merchantStats[mid].gmv,
    total_orders: merchantStats[mid].orders,
    completed_orders: merchantStats[mid].completed,
    updated_at: new Date().toISOString()
  }))
  if (merchantUpserts.length) {
    await supabaseAdmin.from('merchant_daily_metrics').upsert(merchantUpserts)
  }

  // 5. Upsert Partner Metrics
  const partnerUpserts = Object.keys(partnerStats).map(pid => ({
    date: targetDate,
    partner_id: pid,
    completed_jobs: partnerStats[pid].completed,
    earnings: partnerStats[pid].earnings,
    updated_at: new Date().toISOString()
  }))
  if (partnerUpserts.length) {
    await supabaseAdmin.from('partner_daily_metrics').upsert(partnerUpserts)
  }
  
  // 6. Upsert Customer Metrics
  const customerUpserts = Object.keys(customerStats).map(cid => ({
    date: targetDate,
    customer_id: cid,
    orders_placed: customerStats[cid].orders,
    spend: customerStats[cid].spend,
    updated_at: new Date().toISOString()
  }))
  if (customerUpserts.length) {
    await supabaseAdmin.from('customer_daily_metrics').upsert(customerUpserts)
  }

  return {
    gmv,
    totalOrders,
    activeCustomers: activeCustomers.size
  }
}
