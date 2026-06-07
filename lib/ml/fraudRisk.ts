import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

export interface OrderFraudContext {
  customer_id: string;
  order_amount: number;
  payment_method_id?: string;
  ip_address?: string;
  is_new_device?: boolean;
}

export interface FraudRiskResult {
  order_id: string;
  risk_score: number;       // 0-100
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  factors: string[];
  action_recommended: 'APPROVE' | 'MANUAL_REVIEW' | 'BLOCK';
}

/**
 * Deterministic rule-based intelligence for Fraud Risk Scoring.
 */
export async function evaluateFraudRisk(
  orderId: string,
  context: OrderFraudContext
): Promise<FraudRiskResult> {
  console.log(`Evaluating fraud risk for order ${orderId}...`)

  let score = 10
  const factors: string[] = []

  // 1. Order Amount Heuristics
  if (context.order_amount > 500) {
    score += 40
    factors.push('High Order Amount (+40): Order > $500')
  } else if (context.order_amount > 200) {
    score += 20
    factors.push('Elevated Order Amount (+20): Order > $200')
  }

  // 2. Account Age / Velocity (Checking recent orders for this customer)
  const { data: recentOrders, error } = await supabase
    .from('orders')
    .select('id')
    .eq('customer_id', context.customer_id)
    .gte('created_at', new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()) // last 24 hrs

  if (!error && recentOrders) {
    if (recentOrders.length > 5) {
      score += 30
      factors.push(`Velocity Trigger (+30): ${recentOrders.length} orders in 24h`)
    }
  }

  // 3. Device/Network Context
  if (context.is_new_device) {
    score += 15
    factors.push('New Device (+15): Unrecognized device fingerprint')
  }

  if (!context.payment_method_id) {
    score += 10
    factors.push('No saved payment method (+10)')
  }

  // Normalize score
  score = Math.min(100, Math.max(0, score))

  // Determine Level and Action
  let risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' = 'LOW'
  let action_recommended: 'APPROVE' | 'MANUAL_REVIEW' | 'BLOCK' = 'APPROVE'

  if (score >= 80) {
    risk_level = 'CRITICAL'
    action_recommended = 'BLOCK'
  } else if (score >= 60) {
    risk_level = 'HIGH'
    action_recommended = 'MANUAL_REVIEW'
  } else if (score >= 30) {
    risk_level = 'MEDIUM'
    action_recommended = 'APPROVE'
  }

  const result: FraudRiskResult = {
    order_id: orderId,
    risk_score: score,
    risk_level,
    factors,
    action_recommended
  }

  // Persist risk check
  const { error: insertError } = await supabase
    .from('risk_checks')
    .insert([{
      entity_type: 'order',
      entity_id: orderId,
      risk_score: result.risk_score,
      risk_level: result.risk_level,
      factors: result.factors,
      action_taken: result.action_recommended === 'BLOCK' ? 'flagged' : 'passed'
    }])

  if (insertError) {
    console.error('Failed to log risk check:', insertError)
  }

  return result
}
