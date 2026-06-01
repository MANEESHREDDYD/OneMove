'use server'

import { createClient } from '@/utils/supabase/server'
import { CartItem } from '@/store/cartStore'

export async function placeMarketplaceOrder({
  merchantId,
  serviceType,
  items,
  totalAmount,
  paymentMethod,
  address,
  instructions
}: {
  merchantId: string | null
  serviceType: string
  items: CartItem[]
  totalAmount: number
  paymentMethod: string
  address: string
  instructions: string
}) {
  const supabase = await createClient()
  if (!supabase) return { error: "Database setup required" }

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: "Authentication required" }

  // 1. Create the order
  const { data: order, error: orderError } = await supabase
    .from('orders')
    .insert({
      customer_id: user.id,
      merchant_id: merchantId,
      service_type: serviceType,
      status: 'pending',
      total_amount: totalAmount,
      pickup_location: { address: 'Merchant Address' }, // For demo, simplified
      dropoff_location: { address, instructions },
      metadata: { items_count: items.length }
    })
    .select()
    .single()

  if (orderError || !order) {
    console.error('Order creation failed:', orderError)
    return { error: "Failed to place order." }
  }

  // 2. Create order items
  if (items.length > 0) {
    const orderItems = items.map(item => ({
      order_id: order.id,
      product_id: item.id,
      quantity: item.quantity,
      price_at_time: item.price
    }))

    const { error: itemsError } = await supabase.from('order_items').insert(orderItems)
    if (itemsError) console.error('Order items failed:', itemsError)
  }

  // 3. Create payment record
  const { error: paymentError } = await supabase.from('payments').insert({
    order_id: order.id,
    customer_id: user.id,
    amount: totalAmount,
    status: 'succeeded',
    method: paymentMethod
  })

  // 4. Create analytics event
  await supabase.from('analytics_events').insert({
    event_type: 'order_placed',
    user_id: user.id,
    metadata: { order_id: order.id, service: serviceType, total: totalAmount }
  })

  return { success: true, orderId: order.id }
}
