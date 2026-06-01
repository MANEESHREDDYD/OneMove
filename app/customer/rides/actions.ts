'use server'

import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { calculateRideEstimate } from '@/utils/pricing'

export async function requestRide(formData: FormData) {
  const pickupStr = formData.get('pickup') as string
  const dropoffStr = formData.get('dropoff') as string
  const serviceClass = formData.get('serviceClass') as string // 'economy' | 'premium'
  const paymentMethod = formData.get('paymentMethod') as string // 'demo_wallet', 'mock_card', etc.

  if (!pickupStr || !dropoffStr || !serviceClass) {
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

  let pickup, dropoff
  try {
    pickup = JSON.parse(pickupStr)
    dropoff = JSON.parse(dropoffStr)
  } catch (e) {
    return { error: 'Invalid location format' }
  }

  // Calculate final price server-side for integrity
  const estimate = calculateRideEstimate(pickup.address, dropoff.address)
  const finalPrice = serviceClass === 'premium' ? estimate.prices.premium : estimate.prices.economy

  const { data: order, error: orderError } = await supabase.from('orders').insert({
    customer_id: user.id,
    service_type: 'ride',
    status: 'requested',
    total_amount: finalPrice,
    pickup_location: pickup,
    dropoff_location: dropoff
  }).select('id').single()

  if (orderError || !order) {
    return { error: 'Failed to request ride. Please try again.' }
  }

  // Determine Payment Status
  let pStatus = 'pending_demo'
  if (paymentMethod === 'demo_wallet' || paymentMethod === 'mock_card') pStatus = 'paid_demo'
  else if (paymentMethod === 'manual') pStatus = 'manual_review_demo'

  // Insert Payment
  await supabase.from('payments').insert({
    order_id: order.id,
    customer_id: user.id,
    amount: finalPrice,
    method: paymentMethod,
    status: pStatus
  })

  // Insert Status Event
  await supabase.from('order_status_events').insert({
    order_id: order.id,
    status: 'requested',
    notes: 'Ride requested by customer'
  })

  // Insert Analytics Event
  await supabase.from('analytics_events').insert({
    event_type: 'ride_requested',
    user_id: user.id,
    metadata: { order_id: order.id, serviceClass }
  })

  // Redirect to unified tracker
  redirect(`/customer/rides/${order.id}`)
}
