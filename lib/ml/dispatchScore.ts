import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

export interface DispatchCandidate {
  partner_id: string;
  partner_name: string;
  vehicle_type: string;
  distance_km: number;
  rating: number;
  acceptance_rate: number;
}

export interface DispatchScoreResult {
  partner_id: string;
  partner_name: string;
  score: number;
  rank: number;
  factors: string[];
}

/**
 * Deterministic rule-based intelligence for Dispatch Optimization.
 * Ranks available partners for a given order/job based on distance, rating, and reliability.
 */
export async function calculateDispatchScores(
  orderId: string,
  candidates: DispatchCandidate[]
): Promise<DispatchScoreResult[]> {
  console.log(`Calculating dispatch scores for order ${orderId} with ${candidates.length} candidates...`)

  if (!candidates || candidates.length === 0) {
    return []
  }

  const results: DispatchScoreResult[] = candidates.map(candidate => {
    let score = 100
    const factors: string[] = []

    // 1. Distance Penalty (Heaviest weight)
    if (candidate.distance_km <= 2) {
      score += 20
      factors.push('Proximity Bonus (+20): Within 2km')
    } else if (candidate.distance_km > 5 && candidate.distance_km <= 10) {
      score -= 15
      factors.push('Distance Penalty (-15): 5-10km away')
    } else if (candidate.distance_km > 10) {
      score -= 30
      factors.push('High Distance Penalty (-30): >10km away')
    }

    // 2. Rating Modifier
    if (candidate.rating >= 4.9) {
      score += 15
      factors.push('Top Rated Bonus (+15): Rating >= 4.9')
    } else if (candidate.rating < 4.5) {
      score -= 10
      factors.push('Low Rating Penalty (-10): Rating < 4.5')
    }

    // 3. Reliability / Acceptance Rate
    if (candidate.acceptance_rate > 0.95) {
      score += 10
      factors.push('High Reliability Bonus (+10): >95% Acceptance')
    } else if (candidate.acceptance_rate < 0.80) {
      score -= 20
      factors.push('Low Reliability Penalty (-20): <80% Acceptance')
    }

    // Normalize score to 0-100 scale ideally
    score = Math.max(0, Math.min(100, score))

    return {
      partner_id: candidate.partner_id,
      partner_name: candidate.partner_name,
      score,
      rank: 0, // will be set after sorting
      factors
    }
  })

  // Sort descending by score
  results.sort((a, b) => b.score - a.score)

  // Assign ranks
  results.forEach((res, index) => {
    res.rank = index + 1
  })

  // Optionally persist top recommendations to DB
  // This is left as an optional extension. For now, we return it synchronously.

  return results
}
