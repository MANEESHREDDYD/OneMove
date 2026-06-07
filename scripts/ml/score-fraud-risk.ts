import { evaluateFraudRisk, OrderFraudContext } from '../../lib/ml/fraudRisk'
import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

async function main() {
  console.log('--- Running Fraud Risk Scoring Engine ---')

  // Pick a recent order to score
  const { data: orders } = await supabase
    .from('orders')
    .select('id, customer_id, total_amount')
    .order('created_at', { ascending: false })
    .limit(3)

  if (!orders || orders.length === 0) {
    console.log('No orders found to score.')
    return
  }

  for (const order of orders) {
    // We add some deterministic "randomness" to simulate real risk triggers for the demo
    const isNewDevice = Math.random() > 0.7
    const noPaymentMethod = Math.random() > 0.8
    
    // Occasionally simulate a massively high value order
    const simulatedAmount = Math.random() > 0.9 ? Number(order.total_amount) * 10 : Number(order.total_amount)

    const context: OrderFraudContext = {
      customer_id: order.customer_id,
      order_amount: simulatedAmount,
      is_new_device: isNewDevice,
      payment_method_id: noPaymentMethod ? undefined : 'pm_mock_123'
    }

    const result = await evaluateFraudRisk(order.id, context)
    console.log(`\nOrder: ${order.id.split('-')[0]} | Amount: $${simulatedAmount}`)
    console.log(`Risk Score: ${result.risk_score} (${result.risk_level}) -> ACTION: ${result.action_recommended}`)
    if (result.factors.length > 0) {
      console.log('Factors triggered:')
      result.factors.forEach(f => console.log(`  - ${f}`))
    }
  }
}

main()
