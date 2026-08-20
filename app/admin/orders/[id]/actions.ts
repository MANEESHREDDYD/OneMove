'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'
import { requireAdminApi } from '@/lib/auth/dal'

export async function adminUpdateOrderStatus(orderId: string, newStatus: string) {
  const guard = await requireAdminApi()
  if (!guard.ok) return { error: guard.error }

  const supabase = await createClient()
  if (!supabase) return { error: 'Database not connected' }

  const { error } = await supabase
    .from('orders')
    .update({ status: newStatus })
    .eq('id', orderId)

  if (error) {
    return { error: 'Failed to update order' }
  }

  // Record the status event
  await supabase.from('order_status_events').insert({
    order_id: orderId,
    status: newStatus,
    notes: `Admin ${guard.userId} forced status to ${newStatus}`
  })

  // Revalidate everything admin
  revalidatePath('/admin/command-center')
  revalidatePath(`/admin/orders/${orderId}`)

  return { success: true }
}

export async function adminAssignPartner(orderId: string, partnerId: string) {
  const guard = await requireAdminApi()
  if (!guard.ok) return { error: guard.error }

  const supabase = await createClient()
  if (!supabase) return { error: 'Database not connected' }

  const { error } = await supabase
    .from('orders')
    .update({ driver_id: partnerId, status: 'partner_assigned' })
    .eq('id', orderId)

  if (error) return { error: 'Failed to assign partner' }

  await supabase.from('order_status_events').insert({
    order_id: orderId,
    status: 'partner_assigned',
    notes: `Admin assigned partner ${partnerId}`
  })

  revalidatePath(`/admin/orders/${orderId}`)
  return { success: true }
}

export async function adminRefundPayment(orderId: string) {
  const guard = await requireAdminApi()
  if (!guard.ok) return { error: guard.error }

  const supabase = await createClient()
  if (!supabase) return { error: 'Database not connected' }

  const { error } = await supabase
    .from('payments')
    .update({ status: 'refunded_demo' })
    .eq('order_id', orderId)

  if (error) return { error: 'Failed to refund payment' }

  revalidatePath(`/admin/orders/${orderId}`)
  return { success: true }
}
