import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

export interface MerchantReliability {
  merchant_id: string;
  reliability_score: number;
  risk_level: 'EXCELLENT' | 'GOOD' | 'WARNING' | 'CRITICAL';
  factors: string[];
  metrics: {
    total_orders: number;
    cancellation_rate: number;
    avg_prep_time_mins: number;
  };
}

export async function scoreMerchantReliability(): Promise<MerchantReliability[]> {
  console.log('Running Merchant Reliability Scoring engine...')

  const { data: merchants } = await supabase
    .from('profiles')
    .select('id, full_name')
    .eq('role', 'merchant')

  if (!merchants) return []

  const results: MerchantReliability[] = []

  for (const merchant of merchants) {
    const { data: orders } = await supabase
      .from('orders')
      .select('id, status, created_at, metadata')
      .eq('merchant_id', merchant.id)

    if (!orders || orders.length === 0) {
      results.push({
        merchant_id: merchant.id,
        reliability_score: 80, // Default good score for new merchants
        risk_level: 'GOOD',
        factors: ['New Merchant: Baseline Score Applied'],
        metrics: { total_orders: 0, cancellation_rate: 0, avg_prep_time_mins: 15 }
      })
      continue
    }

    const totalOrders = orders.length
    const cancelled = orders.filter(o => o.status === 'cancelled').length
    const cancellationRate = cancelled / totalOrders

    // Simulated average prep time from metadata if it exists, else default 20
    let avgPrepTime = 20
    const ordersWithPrep = orders.filter(o => o.metadata && (o.metadata as any).prep_time_mins)
    if (ordersWithPrep.length > 0) {
      const totalPrep = ordersWithPrep.reduce((sum, o) => sum + ((o.metadata as any).prep_time_mins || 0), 0)
      avgPrepTime = totalPrep / ordersWithPrep.length
    }

    let score = 100
    const factors: string[] = []

    if (cancellationRate > 0.1) {
      score -= (cancellationRate * 100) // Deduct heavily for cancellations
      factors.push(`High Cancellation Rate: ${(cancellationRate * 100).toFixed(1)}%`)
    } else {
      factors.push('Healthy completion rate')
    }

    if (avgPrepTime > 30) {
      score -= 15
      factors.push('Slow Average Prep Time (>30m)')
    } else if (avgPrepTime < 15) {
      score += 5
      factors.push('Fast Prep Time Bonus')
    }

    score = Math.max(0, Math.min(score, 100))
    let riskLevel: 'EXCELLENT' | 'GOOD' | 'WARNING' | 'CRITICAL' = 'GOOD'
    
    if (score >= 90) riskLevel = 'EXCELLENT'
    else if (score >= 70) riskLevel = 'GOOD'
    else if (score >= 50) riskLevel = 'WARNING'
    else riskLevel = 'CRITICAL'

    results.push({
      merchant_id: merchant.id,
      reliability_score: Math.round(score),
      risk_level: riskLevel,
      factors,
      metrics: { total_orders: totalOrders, cancellation_rate: cancellationRate, avg_prep_time_mins: Math.round(avgPrepTime) }
    })
  }

  if (results.length > 0) {
    await supabase.from('merchant_reliability_scores').delete().neq('id', '00000000-0000-0000-0000-000000000000')
    const insertData = results.map(r => ({
      merchant_id: r.merchant_id,
      reliability_score: r.reliability_score,
      risk_level: r.risk_level,
      factors: r.factors,
      metrics: r.metrics
    }))
    await supabase.from('merchant_reliability_scores').insert(insertData)
  }

  return results
}
