import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

export interface RecommendationResult {
  customer_id: string;
  entity_type: 'merchant' | 'ride_destination' | 'item';
  entity_id: string;
  entity_name: string;
  score: number;
  confidence: number;
  reasoning: string[];
}

/**
 * Deterministic rule-based recommendation engine for customers.
 * Suggests merchants, ride destinations, or items based on past order history and current time context.
 */
export async function generateRecommendations(customerId: string): Promise<RecommendationResult[]> {
  console.log(`Generating recommendations for customer ${customerId}...`)

  const results: RecommendationResult[] = []

  // 1. Fetch customer's past orders
  const { data: pastOrders } = await supabase
    .from('orders')
    .select('id, merchant_id, service_type, pickup_location, dropoff_location, created_at')
    .eq('customer_id', customerId)
    .order('created_at', { ascending: false })
    .limit(20)

  const currentHour = new Date().getHours()
  const isMorning = currentHour >= 5 && currentHour <= 10
  const isLunch = currentHour >= 11 && currentHour <= 14
  const isDinner = currentHour >= 17 && currentHour <= 21

  if (!pastOrders || pastOrders.length === 0) {
    // Cold start recommendations
    const { data: popularMerchants } = await supabase
      .from('profiles')
      .select('id, full_name')
      .eq('role', 'merchant')
      .limit(3)

    if (popularMerchants) {
      for (const m of popularMerchants) {
        results.push({
          customer_id: customerId,
          entity_type: 'merchant',
          entity_id: m.id,
          entity_name: m.full_name || 'Popular Merchant',
          score: 50,
          confidence: 0.4,
          reasoning: ['Cold start: Popular in your area']
        })
      }
    }
  } else {
    // Affinity mapping based on history
    const merchantAffinity: Record<string, number> = {}
    const destinationAffinity: Record<string, number> = {}

    pastOrders.forEach(order => {
      if (order.merchant_id) {
        merchantAffinity[order.merchant_id] = (merchantAffinity[order.merchant_id] || 0) + 1
      }
      if (order.service_type === 'ride' && order.dropoff_location) {
        // Simple string matching for demo
        const dest = JSON.stringify(order.dropoff_location)
        destinationAffinity[dest] = (destinationAffinity[dest] || 0) + 1
      }
    })

    // Generate Merchant Recommendations
    const topMerchants = Object.entries(merchantAffinity)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)

    for (const [merchantId, count] of topMerchants) {
      const { data: mData } = await supabase.from('profiles').select('full_name').eq('id', merchantId).single()
      let score = 60 + (count * 5)
      const reasoning = [`Ordered ${count} times previously`]
      
      if (isLunch && count > 2) {
        score += 15
        reasoning.push('Time affinity: Often orders here during lunch')
      } else if (isDinner && count > 2) {
        score += 15
        reasoning.push('Time affinity: Often orders here during dinner')
      }

      results.push({
        customer_id: customerId,
        entity_type: 'merchant',
        entity_id: merchantId,
        entity_name: mData?.full_name || 'Favorite Merchant',
        score: Math.min(score, 100),
        confidence: 0.85,
        reasoning
      })
    }

    // Generate Ride Recommendations
    const topDestinations = Object.entries(destinationAffinity)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)

    for (const [destStr, count] of topDestinations) {
      const dest = JSON.parse(destStr)
      let score = 70 + (count * 2)
      const reasoning = [`Traveled here ${count} times`]
      
      if (isMorning) {
        score += 10
        reasoning.push('Morning commute pattern detected')
      }

      results.push({
        customer_id: customerId,
        entity_type: 'ride_destination',
        entity_id: 'dest_hash', // Abstracting the exact location ID
        entity_name: dest.address || 'Saved Destination',
        score: Math.min(score, 100),
        confidence: 0.78,
        reasoning
      })
    }
  }

  // Persist recommendations
  const records = results.map(r => ({
    customer_id: r.customer_id,
    entity_type: r.entity_type,
    entity_id: r.entity_id,
    score: r.score,
    confidence: r.confidence,
    reasoning: r.reasoning
  }))

  if (records.length > 0) {
    // We optionally delete old ones first to prevent bloat per user
    await supabase.from('recommendations').delete().eq('customer_id', customerId)
    await supabase.from('recommendations').insert(records)
  }

  return results
}
