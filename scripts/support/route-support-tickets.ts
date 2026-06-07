import * as dotenv from 'dotenv'
import path from 'path'
import { createClient } from '@supabase/supabase-js'
import { processNewTicket } from '../../lib/ai/supportAssistant'

const envPath = path.resolve(process.cwd(), '.env.local')
dotenv.config({ path: envPath })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

async function run() {
  if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Missing Supabase env vars')
    process.exit(1)
  }

  const supabase = createClient(supabaseUrl, supabaseServiceKey)

  console.log('--- Running Support Ticket Routing Simulation ---')

  // Pick some recent orders to generate tickets for
  const { data: orders } = await supabase
    .from('orders')
    .select('id, customer_id')
    .order('created_at', { ascending: false })
    .limit(3)

  if (!orders || orders.length === 0) {
    console.log('No orders found to generate tickets for.')
    process.exit(0)
  }

  const demoTickets = [
    { desc: "My food was completely cold and the container was broken.", order: orders[0] },
    { desc: "The partner was driving very unsafely, running red lights.", order: orders[1] },
    { desc: "Where is my order? It is 30 minutes late.", order: orders[2] },
  ]

  for (const t of demoTickets) {
    try {
      const ticket = await processNewTicket(supabaseUrl, supabaseServiceKey, t.order.customer_id, t.desc, t.order.id)
      console.log(`✅ Created ${ticket.priority} ticket for category: ${ticket.category}`)
    } catch (err: any) {
      console.error(`❌ Failed to create ticket:`, err.message)
    }
  }
}

run()
