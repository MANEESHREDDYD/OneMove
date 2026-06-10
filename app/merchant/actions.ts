'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'
import type { OrderStatus } from '@/lib/status/statusTransitions'

export async function updateMerchantOrderStatus(orderId: string, newStatus: string) {
  const supabase = await createClient()
  if (!supabase) {
    return { error: 'Supabase is not configured. See docs/LOCAL_SETUP.md.' }
  }
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    return { error: 'Authentication required' }
  }

  const { data: merchants, error: merchantError } = await supabase
    .from('merchants')
    .select('id')
    .eq('owner_id', user.id)

  if (merchantError) {
    return { error: 'Unable to verify merchant ownership' }
  }

  const merchantIds = merchants?.map((merchant) => merchant.id) || []
  if (merchantIds.length === 0) {
    return { error: 'No merchant profile found for this account' }
  }

  // Ensure order belongs to one of the signed-in merchant account's stores.
  const { data: order, error: fetchError } = await supabase
    .from('orders')
    .select('status, service_type')
    .eq('id', orderId)
    .in('merchant_id', merchantIds)
    .single()

  if (fetchError || !order) {
    return { error: 'Order not found' }
  }

  const { isValidTransition } = await import('@/lib/status/statusTransitions')
  if (!isValidTransition(order.service_type || 'eats', order.status as OrderStatus, newStatus as OrderStatus)) {
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
    notes: `Merchant ${user.id} marked order as ${newStatus}`
  })

  revalidatePath('/merchant')
  
  return { success: true }
}
