'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'

export async function requestCourierOrder(formData: FormData) {
  const supabase = await createClient()
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    return { error: 'Authentication required' }
  }

  const pickupAddress = formData.get('pickupAddress') as string
  const dropoffAddress = formData.get('dropoffAddress') as string
  const packageSize = formData.get('packageSize') as string
  const packageDetails = formData.get('packageDetails') as string

  if (!pickupAddress || !dropoffAddress || !packageSize) {
    return { error: 'Please fill in all required fields' }
  }

  // Base pricing logic based on size
  let basePrice = 10.00
  if (packageSize === 'Medium') basePrice = 15.00
  if (packageSize === 'Large') basePrice = 25.00
  if (packageSize === 'Extra Large') basePrice = 45.00

  const { data: order, error: insertError } = await supabase
    .from('orders')
    .insert({
      customer_id: user.id,
      service_type: 'courier',
      status: 'pending',
      total_amount: basePrice,
      pickup_location: { address: pickupAddress, lat: 0, lng: 0 },
      dropoff_location: { address: dropoffAddress, lat: 0, lng: 0 },
      metadata: { 
        package: {
          size: packageSize,
          details: packageDetails || 'No details provided'
        }
      }
    })
    .select('id')
    .single()

  if (insertError || !order) {
    return { error: 'Failed to request courier' }
  }

  revalidatePath('/customer')
  
  return { success: true, orderId: order.id }
}
