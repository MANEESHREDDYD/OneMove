/**
 * Idempotency Helper
 * Provides consistent methods to generate and handle idempotency keys.
 */
import { v4 as uuidv4 } from 'uuid';

export function generateIdempotencyKey(): string {
  return uuidv4();
}

/**
 * Validates an idempotency key format (UUID v4)
 */
export function isValidIdempotencyKey(key: string | null | undefined): boolean {
  if (!key) return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(key);
}
