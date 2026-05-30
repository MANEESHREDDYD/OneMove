'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'

export async function acceptJob(orderId: string) {
  const supabase = await createClient()
  if (!supabase) {
    return { error: 'Supabase is not configured. See docs/LOCAL_SETUP.md.' }
  }
  const { data: { user }, error: userError } = await supabase.auth.getUser()

  if (userError || !user) {
    return { error: 'Authentication required' }
  }

  // Ensure the order is still pending
  const { data: order, error: fetchError } = await supabase
    .from('orders')
    .select('status')
    .eq('id', orderId)
    .single()

  if (fetchError || !order) {
    return { error: 'Job not found' }
  }

  if (order.status !== 'pending') {
    return { error: 'Job is no longer available' }
  }

  const { error: updateError } = await supabase
    .from('orders')
    .update({ 
      status: 'accepted',
      driver_id: user.id
    })
    .eq('id', orderId)

  if (updateError) {
    return { error: 'Failed to accept job' }
  }

  revalidatePath('/partner')
  return { success: true }
}

export async function updateJobStatus(orderId: string, newStatus: 'in_transit' | 'completed') {
  const supabase = await createClient()
  if (!supabase) {
    return { error: 'Supabase is not configured. See docs/LOCAL_SETUP.md.' }
  }
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Authentication required' }
  }

  const { error: updateError } = await supabase
    .from('orders')
    .update({ status: newStatus })
    .eq('id', orderId)
    .eq('driver_id', user.id) // Security check: must be the assigned driver

  if (updateError) {
    return { error: 'Failed to update job status' }
  }

  revalidatePath('/partner')
  return { success: true }
}
