import crypto from 'crypto'

/**
 * Deterministic hash-based assignment for A/B testing
 * hash(customer_id + experiment_id) % 100
 */
export function getDeterministicAssignment(customerId: string, experimentId: string, totalVariants: number): number {
  if (!customerId || !experimentId || totalVariants <= 0) return 0
  
  const hash = crypto.createHash('md5').update(`${customerId}-${experimentId}`).digest('hex')
  // Parse first 8 chars as an integer and modulo
  const intVal = parseInt(hash.substring(0, 8), 16)
  return intVal % totalVariants
}
