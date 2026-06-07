import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

export interface CustomerSegment {
  customer_id: string;
  segment_name: string;
  feature_values: {
    order_count: number;
    monthly_spend: number;
    cancellation_rate: number;
    recency_days: number;
  };
}

/**
 * Evaluates customer purchasing behavior and assigns segmentation labels deterministically.
 */
export async function segmentCustomers(): Promise<CustomerSegment[]> {
  console.log('Running Customer Segmentation engine...')

  const { data: customers } = await supabase
    .from('profiles')
    .select('id')
    .eq('role', 'customer')

  if (!customers) return []

  const segments: CustomerSegment[] = []
  const now = new Date().getTime()

  for (const customer of customers) {
    const { data: orders } = await supabase
      .from('orders')
      .select('id, amount, status, created_at')
      .eq('customer_id', customer.id)

    if (!orders || orders.length === 0) {
      segments.push({
        customer_id: customer.id,
        segment_name: 'New User',
        feature_values: { order_count: 0, monthly_spend: 0, cancellation_rate: 0, recency_days: -1 }
      })
      continue
    }

    const orderCount = orders.length
    const completedOrders = orders.filter(o => o.status === 'completed')
    const cancelledOrders = orders.filter(o => o.status === 'cancelled')
    
    const monthlySpend = completedOrders.reduce((sum, o) => sum + (Number(o.amount) || 0), 0)
    const cancellationRate = orderCount > 0 ? cancelledOrders.length / orderCount : 0
    
    // Find most recent order
    let latestOrderDate = 0
    orders.forEach(o => {
      const d = new Date(o.created_at).getTime()
      if (d > latestOrderDate) latestOrderDate = d
    })
    const recencyDays = latestOrderDate > 0 ? (now - latestOrderDate) / (1000 * 60 * 60 * 24) : -1

    let segmentName = 'Standard User'
    if (orderCount > 10 && monthlySpend > 500) {
      segmentName = 'High-Value Power User'
    } else if (cancellationRate > 0.3) {
      segmentName = 'High-Risk (Cancellations)'
    } else if (recencyDays > 30) {
      segmentName = 'At-Risk Inactive'
    } else if (orderCount > 5) {
      segmentName = 'Active Regular'
    }

    segments.push({
      customer_id: customer.id,
      segment_name: segmentName,
      feature_values: {
        order_count: orderCount,
        monthly_spend: monthlySpend,
        cancellation_rate: cancellationRate,
        recency_days: Math.round(recencyDays)
      }
    })
  }

  // Persist
  if (segments.length > 0) {
    await supabase.from('customer_segments').delete().neq('id', '00000000-0000-0000-0000-000000000000') // Clear table efficiently
    const insertData = segments.map(s => ({
      customer_id: s.customer_id,
      segment_name: s.segment_name,
      feature_values: s.feature_values
    }))
    await supabase.from('customer_segments').insert(insertData)
  }

  return segments
}
