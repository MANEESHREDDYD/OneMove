import { calculateDispatchScores, DispatchCandidate } from '../../lib/ml/dispatchScore'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

async function main() {
  console.log('--- Running Dispatch Simulation ---')
  
  // Get a pending or searching order to simulate
  const { data: orders } = await supabase
    .from('orders')
    .select('id, pickup_location')
    .limit(1)

  if (!orders || orders.length === 0) {
    console.log('No orders found to simulate dispatch.')
    return
  }

  const order = orders[0]

  // Get some partners
  const { data: partners } = await supabase
    .from('profiles')
    .select('id, full_name, vehicle_type')
    .in('role', ['partner', 'driver'])
    .limit(5)

  if (!partners || partners.length === 0) {
    console.log('No partners found.')
    return
  }

  // Mock candidate attributes for simulation
  const candidates: DispatchCandidate[] = partners.map(p => ({
    partner_id: p.id,
    partner_name: p.full_name || 'Unknown Partner',
    vehicle_type: p.vehicle_type || 'car',
    distance_km: Number((Math.random() * 15).toFixed(1)), // 0 to 15km
    rating: Number((4.0 + Math.random() * 1.0).toFixed(2)), // 4.0 to 5.0
    acceptance_rate: Number((0.7 + Math.random() * 0.3).toFixed(2)) // 70% to 100%
  }))

  const results = await calculateDispatchScores(order.id, candidates)

  console.log(`\nDispatch rankings for Order ${order.id.split('-')[0]}:`)
  console.table(results.map(r => ({
    Rank: r.rank,
    Partner: r.partner_name,
    Score: r.score,
    TopFactor: r.factors.length > 0 ? r.factors[0] : 'None'
  })))
}

main()
