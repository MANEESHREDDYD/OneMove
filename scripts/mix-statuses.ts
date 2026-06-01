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

async function mixStatuses() {
  console.log('=== Mixing Seed Data Statuses ===')
  
  const { data: orders } = await supabase.from('orders').select('id, service_type')
  if (!orders) return
  
  const eGroceryStatuses = ['placed', 'merchant_accepted', 'preparing', 'ready', 'partner_assigned', 'picked_up', 'in_transit', 'delivered', 'completed']
  const rideStatuses = ['requested', 'partner_assigned', 'arrived', 'started', 'completed']
  
  let count = 0
  for (const order of orders) {
    if (Math.random() > 0.3) {
      let newStatus = 'placed'
      if (order.service_type === 'ride') {
        newStatus = rideStatuses[Math.floor(Math.random() * rideStatuses.length)]
      } else {
        newStatus = eGroceryStatuses[Math.floor(Math.random() * eGroceryStatuses.length)]
      }
      
      await supabase.from('orders').update({ status: newStatus }).eq('id', order.id)
      
      // Attempt to assign a driver randomly if applicable
      if (['partner_assigned', 'picked_up', 'in_transit', 'delivered', 'completed', 'arrived', 'started'].includes(newStatus)) {
         const { data: drivers } = await supabase.from('profiles').select('id').eq('role', 'partner').limit(1)
         if (drivers && drivers.length > 0) {
            await supabase.from('orders').update({ driver_id: drivers[0].id }).eq('id', order.id)
         }
      }
      count++
    }
  }
  
  console.log(`✅ Mixed statuses for ${count} orders.`)
}

mixStatuses().catch(console.error)
