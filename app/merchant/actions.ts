'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'

export async function updateMerchantOrderStatus(orderId: string, newStatus: string) {
  const supabase = await createClient()
  if (!supabase) {
    return { error: 'Supabase is not configured. See docs/LOCAL_SETUP.md.' }
  }
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    return { error: 'Authentication required' }
  }

  // Ensure order is accessible (In a real app, we would verify this order belongs to the merchant's restaurant)
  const { data: order, error: fetchError } = await supabase
    .from('orders')
    .select('status, service_type')
    .eq('id', orderId)
    .single()

  if (fetchError || !order) {
    return { error: 'Order not found' }
  }

  const { isValidTransition } = await import('@/lib/status/statusTransitions')
  if (!isValidTransition(order.service_type || 'eats', order.status as any, newStatus as any)) {
    return { error: `Invalid status transition from ${order.status} to ${newStatus}` }
  }

  // Update status
  const { error: updateError } = await supabase
    .from('orders')
    .update({ status: newStatus })
    .eq('id', orderId)

  if (updateError) {
    return { error: 'Failed to update order status' }
  }

  // Record the event
  await supabase.from('order_status_events').insert({
    order_id: orderId,
    status: newStatus,
    changed_by: user.id,
    notes: `Merchant marked order as ${newStatus}`
  })

  revalidatePath('/merchant')
  
  return { success: true }
}
