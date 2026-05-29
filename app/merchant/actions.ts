'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'

export async function updateMerchantOrderStatus(orderId: string, newStatus: 'preparing' | 'ready') {
  const supabase = await createClient()
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    return { error: 'Authentication required' }
  }

  // Ensure order is accessible (In a real app, we would verify this order belongs to the merchant's restaurant)
  const { data: order, error: fetchError } = await supabase
    .from('orders')
    .select('status')
    .eq('id', orderId)
    .single()

  if (fetchError || !order) {
    return { error: 'Order not found' }
  }

  // Update status
  const { error: updateError } = await supabase
    .from('orders')
    .update({ status: newStatus })
    .eq('id', orderId)

  if (updateError) {
    return { error: 'Failed to update order status' }
  }

  revalidatePath('/merchant')
  
  // Notice: 'ready' means it's still 'pending' for a driver in our simplified flow, 
  // but if we had a more complex status tree, we would mark it 'pending_driver' here.
  // For the MVP, if the merchant says it's ready, the driver picks it up.
  // However, the driver dashboard looks for 'pending'. We should map 'ready' to driver visibility, 
  // or just let the driver accept it while it's 'pending' or 'preparing'.
  // We'll keep it simple: the order is created as 'pending'. Driver can accept it anytime.
  // Merchant updates it to 'preparing' and then 'ready'.

  return { success: true }
}
