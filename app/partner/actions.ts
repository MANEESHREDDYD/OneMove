'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'

export async function acceptJob(orderId: string) {
  const supabase = await createClient()
  if (!supabase) return { error: "Database setup required" }

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: "Authentication required" }

  // Check if job is still available
  const { data: order } = await supabase
    .from('orders')
    .select('status, driver_id')
    .eq('id', orderId)
    .single()

  if (!order || !['pending', 'placed', 'merchant_accepted', 'preparing', 'ready', 'requested', 'created'].includes(order.status) || order.driver_id !== null) {
    return { error: "Job is no longer available" }
  }

  const { data: updatedOrder, error } = await supabase
    .from('orders')
    .update({
      driver_id: user.id,
      status: 'accepted'
    })
    .eq('id', orderId)
    .is('driver_id', null)
    .select('id')
    .single()

  if (error || !updatedOrder) {
    console.error('Accept job error:', error)
    return { error: "Failed to accept job. It may have been taken by another partner." }
  }

  await supabase.from('order_status_events').insert({
    order_id: orderId,
    status: 'accepted',
    notes: 'Partner assigned'
  })
  
  await supabase.from('analytics_events').insert({
    event_type: 'partner_assigned',
    user_id: user.id,
    metadata: { order_id: orderId }
  })

  revalidatePath('/partner/jobs')
  revalidatePath('/partner')
  return { success: true }
}

export async function updateJobStatus(orderId: string, newStatus: string) {
  const supabase = await createClient()
  if (!supabase) return { error: "Database setup required" }

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: "Authentication required" }

  const { data: order } = await supabase.from('orders').select('status, service_type').eq('id', orderId).single()
  
  if (!order) return { error: "Order not found" }

  const { isValidTransition } = await import('@/lib/status/statusTransitions')
  if (!isValidTransition(order.service_type || 'eats', order.status as any, newStatus as any)) {
    return { error: `Invalid transition from ${order.status} to ${newStatus}` }
  }

  const { error } = await supabase
    .from('orders')
    .update({ status: newStatus })
    .eq('id', orderId)
    .eq('driver_id', user.id)

  if (error) {
    return { error: "Failed to update status" }
  }

  await supabase.from('order_status_events').insert({
    order_id: orderId,
    status: newStatus,
  })

  if (newStatus === 'completed') {
    // Generate partner earnings
    const { data: order } = await supabase.from('orders').select('total_amount').eq('id', orderId).single()
    if (order) {
      const payout = order.total_amount * 0.75; // 75% goes to driver
      await supabase.from('partner_earnings').insert({
        partner_id: user.id,
        order_id: orderId,
        amount: payout,
        description: `Payout for order ${orderId.split('-')[0]}`
      })
      await supabase.from('analytics_events').insert({
        event_type: 'delivery_completed',
        user_id: user.id,
        metadata: { order_id: orderId, payout }
      })
    }
  }

  revalidatePath('/partner/jobs')
  revalidatePath('/partner/earnings')
  revalidatePath('/partner')
  return { success: true }
}
