import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'

dotenv.config({ path: '.env.local' })

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

type OrderRow = {
  customer_id: string | null
  service_type: string | null
  status: string | null
  total_amount: number | null
  created_at: string
}

type CustomerAccumulator = {
  totalOrders: number
  completedOrders: number
  cancelledOrders: number
  gmv: number
  rideOrders: number
  eatsOrders: number
  groceryOrders: number
  courierOrders: number
  lastOrderAt: string
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10)
}

function daysSince(date: string) {
  const elapsedMs = Date.now() - new Date(date).getTime()
  return Math.max(0, Math.round(elapsedMs / 86_400_000))
}

function emptyAccumulator(createdAt: string): CustomerAccumulator {
  return {
    totalOrders: 0,
    completedOrders: 0,
    cancelledOrders: 0,
    gmv: 0,
    rideOrders: 0,
    eatsOrders: 0,
    groceryOrders: 0,
    courierOrders: 0,
    lastOrderAt: createdAt,
  }
}

async function run() {
  console.log('--- STARTING FEATURE SNAPSHOTS ---')
  const { data: runData, error: runErr } = await supabaseAdmin
    .from('data_pipeline_runs')
    .insert({
      pipeline_name: 'feature_snapshots',
      status: 'running',
    })
    .select('id')
    .single()

  if (runErr) {
    console.error('Failed to start pipeline:', runErr)
    process.exit(1)
  }

  const runId = runData.id

  try {
    console.log('Computing deterministic feature snapshots from orders...')

    const since = new Date()
    since.setDate(since.getDate() - 30)

    const { data, error } = await supabaseAdmin
      .from('orders')
      .select('customer_id, service_type, status, total_amount, created_at')
      .gte('created_at', since.toISOString())
      .order('created_at', { ascending: false })

    if (error) throw error

    const orders = (data || []) as OrderRow[]
    const byCustomer = new Map<string, CustomerAccumulator>()

    for (const order of orders) {
      if (!order.customer_id) continue

      const current = byCustomer.get(order.customer_id) || emptyAccumulator(order.created_at)
      current.totalOrders += 1

      if (order.status === 'completed' || order.status === 'delivered') {
        current.completedOrders += 1
        current.gmv += Number(order.total_amount || 0)
      }

      if (order.status === 'cancelled') current.cancelledOrders += 1
      if (order.service_type === 'ride') current.rideOrders += 1
      if (order.service_type === 'eats') current.eatsOrders += 1
      if (order.service_type === 'grocery') current.groceryOrders += 1
      if (order.service_type === 'courier') current.courierOrders += 1
      if (new Date(order.created_at) > new Date(current.lastOrderAt)) {
        current.lastOrderAt = order.created_at
      }

      byCustomer.set(order.customer_id, current)
    }

    const snapshotDate = todayIsoDate()
    await supabaseAdmin
      .from('feature_snapshots')
      .delete()
      .eq('snapshot_date', snapshotDate)
      .in('entity_type', ['customer', 'global'])

    const customerRows = Array.from(byCustomer.entries()).map(([customerId, stats]) => ({
      entity_id: customerId,
      entity_type: 'customer',
      snapshot_date: snapshotDate,
      features: {
        customer_order_count_30d: stats.completedOrders,
        customer_total_orders_30d: stats.totalOrders,
        customer_gmv_30d: Number(stats.gmv.toFixed(2)),
        customer_cancel_rate:
          stats.totalOrders > 0 ? Number((stats.cancelledOrders / stats.totalOrders).toFixed(4)) : 0,
        ride_order_count_30d: stats.rideOrders,
        eats_order_count_30d: stats.eatsOrders,
        grocery_order_count_30d: stats.groceryOrders,
        courier_order_count_30d: stats.courierOrders,
        days_since_last_order: daysSince(stats.lastOrderAt),
      },
    }))

    const activeOrders = orders.filter((order) =>
      ['pending', 'placed', 'accepted', 'preparing', 'ready', 'in_transit', 'requested'].includes(
        order.status || ''
      )
    ).length

    const completedOrders = orders.filter((order) =>
      ['completed', 'delivered'].includes(order.status || '')
    ).length

    const totalGmv = orders
      .filter((order) => ['completed', 'delivered'].includes(order.status || ''))
      .reduce((sum, order) => sum + Number(order.total_amount || 0), 0)

    const globalFeatures = {
      order_count_30d: orders.length,
      active_order_count: activeOrders,
      completed_order_count_30d: completedOrders,
      unique_customer_count_30d: byCustomer.size,
      gmv_30d: Number(totalGmv.toFixed(2)),
      demand_intensity_score: Math.min(100, activeOrders * 5 + byCustomer.size),
    }

    const rows = [
      ...customerRows,
      {
        entity_id: null,
        entity_type: 'global',
        snapshot_date: snapshotDate,
        features: globalFeatures,
      },
    ]

    if (rows.length > 0) {
      const { error: insertError } = await supabaseAdmin.from('feature_snapshots').insert(rows)
      if (insertError) throw insertError
    }

    await supabaseAdmin.from('metric_snapshots').insert({
      metric_name: 'global_demand_intensity',
      metric_value: globalFeatures.demand_intensity_score,
      dimensions: { region: 'all', source: 'feature_snapshots' },
    })

    await supabaseAdmin
      .from('data_pipeline_runs')
      .update({
        status: 'success',
        end_time: new Date().toISOString(),
        rows_processed: rows.length,
      })
      .eq('id', runId)

    console.log(`--- FEATURE SNAPSHOTS SUCCESS (${rows.length} rows) ---`)
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err)
    console.error('Pipeline Error:', message)
    await supabaseAdmin
      .from('data_pipeline_runs')
      .update({
        status: 'failed',
        end_time: new Date().toISOString(),
        error_message: message,
      })
      .eq('id', runId)
    process.exit(1)
  }
}

run()
