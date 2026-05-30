'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { calculateRideEstimate } from '@/utils/pricing'

export async function requestRide(formData: FormData) {
  const pickup = formData.get('pickup') as string
  const dropoff = formData.get('dropoff') as string
  const serviceClass = formData.get('serviceClass') as string // 'economy' | 'premium'

  if (!pickup || !dropoff || !serviceClass) {
    return { error: 'Missing required fields.' }
  }

  const supabase = await createClient()
  if (!supabase) {
    return { error: 'Supabase is not configured. See docs/LOCAL_SETUP.md.' }
  }
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    redirect('/auth/login')
  }

  // Calculate final price server-side for integrity
  const estimate = calculateRideEstimate(pickup, dropoff)
  const finalPrice = serviceClass === 'premium' ? estimate.prices.premium : estimate.prices.economy

  const pickupJson = { address: pickup, lat: 0, lng: 0 }
  const dropoffJson = { address: dropoff, lat: 0, lng: 0 }

  const { error: orderError } = await supabase.from('orders').insert({
    customer_id: user.id,
    service_type: 'ride',
    status: 'pending',
    total_amount: finalPrice,
    pickup_location: pickupJson,
    dropoff_location: dropoffJson
  })

  if (orderError) {
    return { error: 'Failed to request ride. Please try again.' }
  }

  // Redirect to dashboard where the active order widget will pick it up
  redirect('/customer')
}
