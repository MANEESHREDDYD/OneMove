'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'

export async function placeGroceryOrder(storeId: string, storeName: string, items: { id: string, name: string, price: number, quantity: number }[], totalAmount: number) {
  const supabase = await createClient()
  if (!supabase) {
    return { error: 'Supabase is not configured. See docs/LOCAL_SETUP.md.' }
  }
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    return { error: 'Authentication required' }
  }

  if (!items || items.length === 0) {
    return { error: 'Cart is empty' }
  }

  const { data: order, error: insertError } = await supabase
    .from('orders')
    .insert({
      customer_id: user.id,
      merchant_id: storeId,
      service_type: 'grocery',
      status: 'pending',
      total_amount: totalAmount,
      pickup_location: { address: storeName, lat: 0, lng: 0 },
      dropoff_location: { address: 'My Home Address', lat: 0, lng: 0 },
      metadata: { items }
    })
    .select('id')
    .single()

  if (insertError || !order) {
    return { error: 'Failed to place grocery order' }
  }

  revalidatePath('/customer')
  revalidatePath('/merchant')
  
  return { success: true, orderId: order.id }
}
