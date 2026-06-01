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

async function debugMerchantOrders() {
  console.log('=== Merchant Orders QA Audit ===')
  
  const { data: merchants } = await supabase.from('merchants').select('*').limit(5)
  if (!merchants || merchants.length === 0) {
    console.error('❌ No merchants found.')
    process.exit(1)
  }

  console.log(`✅ Found ${merchants.length} merchants.`)

  const merchantIds = merchants.map(m => m.id)

  const { data: orders, error: ordersError } = await supabase
    .from('orders')
    .select('*')
    .in('merchant_id', merchantIds)

  if (ordersError) {
    console.error('❌ Error fetching merchant orders:', ordersError)
  } else {
    console.log(`✅ Found ${orders.length} orders across ${merchants.length} merchants.`)
    const statusBreakdown = orders.reduce((acc: any, order) => {
      acc[order.status] = (acc[order.status] || 0) + 1
      return acc
    }, {})
    console.table(statusBreakdown)
  }

  console.log('=== Merchant QA Complete ===')
}

debugMerchantOrders().catch(console.error)
