'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'

export async function cancelOrder(orderId: string) {
  const supabase = await createClient()
  if (!supabase) {
    return { error: 'Supabase is not configured. See docs/LOCAL_SETUP.md.' }
  }
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    return { error: 'Authentication required' }
  }

  // Ensure order belongs to user and is in a state that can be canceled
  const { data: order, error: fetchError } = await supabase
    .from('orders')
    .select('status, customer_id')
    .eq('id', orderId)
    .single()

  if (fetchError || !order) {
    return { error: 'Order not found' }
  }

  if (order.customer_id !== user.id) {
    return { error: 'Unauthorized' }
  }

  if (!['pending', 'placed', 'merchant_accepted', 'accepted'].includes(order.status)) {
    return { error: 'Order cannot be canceled at this stage' }
  }

  const { error: updateError } = await supabase
    .from('orders')
    .update({ status: 'cancelled' })
    .eq('id', orderId)

  if (updateError) {
    return { error: 'Failed to cancel order' }
  }

  revalidatePath('/customer')
  revalidatePath(`/customer/orders/${orderId}`)
  
  return { success: true }
}
