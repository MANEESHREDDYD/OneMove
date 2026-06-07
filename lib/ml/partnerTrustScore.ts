import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

export interface PartnerTrust {
  partner_id: string;
  trust_score: number;
  status: 'TRUSTED' | 'PROBATION' | 'AT_RISK';
  factors: string[];
  metrics: {
    total_jobs: number;
    completion_rate: number;
    avg_rating: number;
  };
}

export async function scorePartnerTrust(): Promise<PartnerTrust[]> {
  console.log('Running Partner Trust Scoring engine...')

  const { data: partners } = await supabase
    .from('profiles')
    .select('id, full_name')
    .eq('role', 'driver')

  if (!partners) return []

  const results: PartnerTrust[] = []

  for (const partner of partners) {
    const { data: jobs } = await supabase
      .from('orders')
      .select('id, status, metadata')
      .eq('driver_id', partner.id)

    if (!jobs || jobs.length === 0) {
      results.push({
        partner_id: partner.id,
        trust_score: 85, // New partners start with a clean, high slate
        status: 'TRUSTED',
        factors: ['New Partner: Clean Slate'],
        metrics: { total_jobs: 0, completion_rate: 1.0, avg_rating: 5.0 }
      })
      continue
    }

    const totalJobs = jobs.length
    const completed = jobs.filter(j => j.status === 'completed').length
    const cancelled = jobs.filter(j => j.status === 'cancelled').length
    
    const completionRate = totalJobs > 0 ? completed / totalJobs : 0
    const cancelRate = totalJobs > 0 ? cancelled / totalJobs : 0

    // Simulate rating from metadata if present
    let totalRating = 0
    let ratingCount = 0
    jobs.forEach(j => {
      if (j.metadata && (j.metadata as any).partner_rating) {
        totalRating += (j.metadata as any).partner_rating
        ratingCount++
      }
    })
    
    const avgRating = ratingCount > 0 ? totalRating / ratingCount : 5.0

    let score = 100
    const factors: string[] = []

    if (completionRate < 0.8) {
      score -= ((1 - completionRate) * 100)
      factors.push(`Low Completion Rate: ${(completionRate * 100).toFixed(0)}%`)
    } else {
      factors.push(`High Completion Rate: ${(completionRate * 100).toFixed(0)}%`)
    }

    if (avgRating < 4.5) {
      score -= ((4.5 - avgRating) * 20)
      factors.push(`Rating below SLA: ${avgRating.toFixed(1)}`)
    }

    if (cancelRate > 0.1) {
      score -= 20
      factors.push(`Elevated Cancellation Rate: ${(cancelRate * 100).toFixed(0)}%`)
    }

    score = Math.max(0, Math.min(score, 100))
    
    let status: 'TRUSTED' | 'PROBATION' | 'AT_RISK' = 'TRUSTED'
    if (score < 60) status = 'AT_RISK'
    else if (score < 80) status = 'PROBATION'

    results.push({
      partner_id: partner.id,
      trust_score: Math.round(score),
      status,
      factors,
      metrics: { total_jobs: totalJobs, completion_rate: completionRate, avg_rating: avgRating }
    })
  }

  if (results.length > 0) {
    await supabase.from('partner_trust_scores').delete().neq('id', '00000000-0000-0000-0000-000000000000')
    const insertData = results.map(r => ({
      partner_id: r.partner_id,
      trust_score: r.trust_score,
      status: r.status,
      factors: r.factors,
      metrics: r.metrics
    }))
    await supabase.from('partner_trust_scores').insert(insertData)
  }

  return results
}
