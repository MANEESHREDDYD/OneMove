/**
 * OneMove Pricing & Utility Engine
 * Mock implementation for MVP to calculate dynamic pricing and distance.
 */

// Simple string hash to generate deterministic pseudo-random numbers
function simpleHash(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i)
    hash |= 0 // Convert to 32bit integer
  }
  return Math.abs(hash)
}

export interface RideEstimate {
  distanceMiles: number
  durationMinutes: number
  surgeMultiplier: number
  confidenceScore: number
  nearestPartnerMinutes: number
  fareExplanation: string
  carbonEstimateKg: number
  prices: {
    economy: FareBreakdown
    comfort: FareBreakdown
    xl: FareBreakdown
    premium: FareBreakdown
  }
}

export interface FareBreakdown {
  base: number
  distance: number
  time: number
  platform: number
  tax: number
  total: number
}

function calculateBreakdown(base: number, distRate: number, timeRate: number, dist: number, time: number, surge: number): FareBreakdown {
  const baseFare = base
  const distanceFare = dist * distRate
  const timeFare = time * timeRate
  const subtotal = (baseFare + distanceFare + timeFare) * surge
  const platform = Number((subtotal * 0.1).toFixed(2)) // 10% platform fee
  const tax = Number((subtotal * 0.08875).toFixed(2)) // NYC tax
  const total = Number((subtotal + platform + tax).toFixed(2))

  return {
    base: Number(baseFare.toFixed(2)),
    distance: Number(distanceFare.toFixed(2)),
    time: Number(timeFare.toFixed(2)),
    platform,
    tax,
    total
  }
}

export function calculateRideEstimate(pickup: string, dropoff: string, pickupZone: string = 'Midtown'): RideEstimate {
  if (!pickup || !dropoff) {
    return {
      distanceMiles: 0,
      durationMinutes: 0,
      surgeMultiplier: 1.0,
      confidenceScore: 0,
      nearestPartnerMinutes: 0,
      fareExplanation: '',
      carbonEstimateKg: 0,
      prices: {
        economy: calculateBreakdown(0,0,0,0,0,1),
        comfort: calculateBreakdown(0,0,0,0,0,1),
        xl: calculateBreakdown(0,0,0,0,0,1),
        premium: calculateBreakdown(0,0,0,0,0,1)
      }
    }
  }

  const hash = simpleHash(pickup + dropoff)
  const distanceMiles = Number(((hash % 240) / 10 + 1).toFixed(1))
  const durationMinutes = Math.ceil((distanceMiles / 20) * 60) + (hash % 10)

  // Advanced pseudo-deterministic rules
  const baseSurge = 1.0 + ((new Date().getMinutes() % 15) / 50)
  const zoneHash = simpleHash(pickupZone)
  const isHighDemand = zoneHash % 3 === 0
  const surgeMultiplier = isHighDemand ? Number((baseSurge + 0.2).toFixed(2)) : Number(baseSurge.toFixed(2))

  const nearestPartnerMinutes = Math.max(1, (hash % 8) + 1)
  const confidenceScore = 95 - (distanceMiles > 10 ? 15 : 0) - (surgeMultiplier > 1.2 ? 10 : 0)

  let fareExplanation = isHighDemand 
    ? `Fare is higher because ${pickupZone} demand is elevated and available partner supply is low.` 
    : `Standard pricing applies. Partner supply in ${pickupZone} is optimal.`

  const carbonEstimateKg = Number((distanceMiles * 0.411).toFixed(1)) // average kg CO2 per mile

  return {
    distanceMiles,
    durationMinutes,
    surgeMultiplier,
    confidenceScore,
    nearestPartnerMinutes,
    fareExplanation,
    carbonEstimateKg,
    prices: {
      economy: calculateBreakdown(2, 1.5, 0.2, distanceMiles, durationMinutes, surgeMultiplier),
      comfort: calculateBreakdown(3, 1.8, 0.25, distanceMiles, durationMinutes, surgeMultiplier),
      xl: calculateBreakdown(4, 2.2, 0.3, distanceMiles, durationMinutes, surgeMultiplier),
      premium: calculateBreakdown(5, 2.5, 0.4, distanceMiles, durationMinutes, surgeMultiplier)
    }
  }
}
