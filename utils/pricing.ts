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
  prices: {
    economy: number
    premium: number
  }
}

export function calculateRideEstimate(pickup: string, dropoff: string): RideEstimate {
  // If inputs are empty, return 0
  if (!pickup || !dropoff) {
    return {
      distanceMiles: 0,
      durationMinutes: 0,
      prices: { economy: 0, premium: 0 }
    }
  }

  // Generate a deterministic distance between 1.0 and 25.0 miles based on addresses
  const hash = simpleHash(pickup + dropoff)
  const distanceMiles = Number(((hash % 240) / 10 + 1).toFixed(1))
  
  // Assume average speed of 20 mph in city traffic
  const durationMinutes = Math.ceil((distanceMiles / 20) * 60)

  // Base pricing model
  // Economy: $2 base + $1.50 per mile + $0.20 per minute
  // Premium: $5 base + $2.50 per mile + $0.40 per minute
  const economyPrice = 2 + (distanceMiles * 1.5) + (durationMinutes * 0.2)
  const premiumPrice = 5 + (distanceMiles * 2.5) + (durationMinutes * 0.4)

  // Add slight dynamic surge multiplier (1.0x to 1.3x) based on the minute of the hour
  // To simulate real-time surge without a real backend daemon
  const surgeMultiplier = 1.0 + ((new Date().getMinutes() % 15) / 50)

  return {
    distanceMiles,
    durationMinutes,
    prices: {
      economy: Number((economyPrice * surgeMultiplier).toFixed(2)),
      premium: Number((premiumPrice * surgeMultiplier).toFixed(2))
    }
  }
}
