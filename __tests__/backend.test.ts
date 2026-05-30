import { describe, it, expect, vi } from 'vitest'

// Mock next/headers and next/navigation for Server Actions
vi.mock('next/headers', () => ({
  cookies: () => ({
    get: vi.fn(),
    set: vi.fn(),
    getAll: vi.fn(),
  }),
}))

vi.mock('next/navigation', () => ({
  redirect: vi.fn((url: string) => { throw new Error(`Redirected to ${url}`) }),
}))

// Import the server actions to test them
import { login } from '../app/auth/actions'
import { requestRide } from '../app/customer/rides/actions'

describe('Backend Server Actions', () => {
  it('login action should fail gracefully with invalid input', async () => {
    const formData = new FormData()
    formData.append('email', 'not-an-email')
    formData.append('password', '123') // too short, invalid
    
    // Auth actions usually return an error or redirect
    try {
      await login(formData)
    } catch (error: Error | unknown) {
      if (error instanceof Error) {
        expect(error.message).toMatch(/Redirected to/)
      }
    }
  })

  it('requestRide action should handle null safety', async () => {
    // Calling without valid session should return { error: ... } or redirect
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
})
