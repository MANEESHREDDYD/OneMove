import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import path from 'path'

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('Missing Supabase credentials in .env.local')
  process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseServiceKey)

async function debugRideBooking() {
  console.log('=== Ride Booking QA Audit ===')
  
  // Find customer demo user
  const { data: customer } = await supabase.from('profiles').select('*').eq('role', 'customer').limit(1).single()
  if (!customer) {
    console.error('❌ No customer user found.')
    process.exit(1)
  }

  console.log(`✅ Found customer: ${customer.id}`)

  // Create mock ride
  const pickup = { address: 'JFK Airport', lat: 40.6413, lng: -73.7781 }
  const dropoff = { address: 'Times Square', lat: 40.758, lng: -73.9855 }
  const finalPrice = 45.50
  
  const { data: order, error: orderError } = await supabase.from('orders').insert({
    customer_id: customer.id,
    service_type: 'ride',
    status: 'requested',
    total_amount: finalPrice,
    pickup_location: pickup,
    dropoff_location: dropoff
  }).select('id').single()

  if (orderError || !order) {
    console.error('❌ Failed to create ride record:', orderError)
    process.exit(1)
  }

  console.log(`✅ Ride record created successfully: ${order.id}`)

  // Create payment record
  const { error: paymentError } = await supabase.from('payments').insert({
    order_id: order.id,
    customer_id: customer.id,
    amount: finalPrice,
    method: 'demo_wallet',
    status: 'paid_demo'
  })

  if (paymentError) {
    console.error('❌ Failed to create payment:', paymentError)
  } else {
    console.log('✅ Payment record created successfully.')
  }

  // Create status event
  const { error: eventError } = await supabase.from('order_status_events').insert({
    order_id: order.id,
    status: 'requested',
    notes: 'Ride requested by customer'
  })

  if (eventError) {
    console.error('❌ Failed to create status event:', eventError)
  } else {
    console.log('✅ Status event created successfully.')
  }

  console.log('=== Ride Booking QA Complete ===')
}

debugRideBooking().catch(console.error)
