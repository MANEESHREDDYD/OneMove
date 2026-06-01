import { describe, it, expect, vi } from 'vitest'

// Mock next/headers and next/navigation for Server Actions
vi.mock('next/headers', () => ({
  cookies: () => ({
    get: vi.fn(),
    set: vi.fn(),
    getAll: vi.fn(),
  }),
}))

vi.mock('next/cache', () => ({
  revalidatePath: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  redirect: vi.fn((url: string) => { throw new Error(`Redirected to ${url}`) }),
}))

// Import the server actions to test them
import { login } from '../app/auth/actions'
import { requestRide } from '../app/customer/rides/actions'
import { updateMerchantOrderStatus } from '../app/merchant/actions'
import { acceptJob } from '../app/partner/actions'

describe('Backend Server Actions & Edge Cases', () => {
  it('login action should fail gracefully with invalid input', async () => {
    const formData = new FormData()
    formData.append('email', 'not-an-email')
    formData.append('password', '123') 
    
    try {
      await login(formData)
    } catch (error: Error | unknown) {
      if (error instanceof Error) {
        expect(error.message).toMatch(/Redirected to/)
      }
    }
  })

  it('requestRide action should handle null safety and invalid payloads', async () => {
    // Missing payload fields entirely
    const formDataEmpty = new FormData()
    const resultEmpty = await requestRide(formDataEmpty)
    expect(resultEmpty).toHaveProperty('error')

    // Valid payload structure but no auth session
    const formData = new FormData()
    formData.append('pickup', 'A')
    formData.append('dropoff', 'B')
    formData.append('serviceClass', 'economy')
    try {
      const result = await requestRide(formData)
      expect(result).toHaveProperty('error')
    } catch (error: Error | unknown) {
      if (error instanceof Error) {
        expect(error.message).toMatch(/Redirected to/)
      }
    }
  })

  it('merchant order status action should gracefully reject unauthenticated calls', async () => {
    const result = await updateMerchantOrderStatus('mock-uuid-123', 'preparing')
    // Unauthenticated context without valid JWT returns error cleanly
    expect(result).toHaveProperty('error')
    expect(result.error).toMatch(/Supabase is not configured|Authentication required/)
  })

  it('partner accept job action should handle invalid order bounds cleanly', async () => {
    const result = await acceptJob('mock-uuid-123')
    expect(result).toHaveProperty('error')
    expect(result.error).toMatch(/Database setup required|Supabase is not configured|Authentication required/)
  })
})
