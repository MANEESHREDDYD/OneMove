'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'

export async function placeEatsOrder(restaurantId: string, restaurantName: string, items: { id: string, name: string, price: number, quantity: number }[], totalAmount: number) {
  const supabase = await createClient()
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    return { error: 'Authentication required' }
  }

  if (!items || items.length === 0) {
    return { error: 'Cart is empty' }
  }

  // Create order
  const { data: order, error: insertError } = await supabase
    .from('orders')
    .insert({
      customer_id: user.id,
      service_type: 'eats',
      status: 'pending',
      total_amount: totalAmount,
      pickup_location: { address: restaurantName, lat: 0, lng: 0 },
      dropoff_location: { address: 'My Home Address', lat: 0, lng: 0 },
      metadata: { items }
    })
    .select('id')
    .single()

  if (insertError || !order) {
    return { error: 'Failed to place order' }
  }

  revalidatePath('/customer')
  revalidatePath('/merchant') // In a real app, this would be specific to the merchant
  
  return { success: true, orderId: order.id }
}
