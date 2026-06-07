import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'
import { computeDailyMetrics } from '../../lib/metrics/computeMetrics'

dotenv.config({ path: '.env.local' })

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

async function refreshMetricStore() {
  console.log('Refreshing Metric Store (Last 7 Days)...')

  for (let i = 0; i < 7; i++) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const targetDate = d.toISOString().split('T')[0]
    
    console.log(`Aggregating metrics for ${targetDate}`)
    await computeDailyMetrics(supabaseAdmin, targetDate)
  }

  console.log('✅ Metric Store Refresh Complete.')
}

refreshMetricStore().catch(e => {
  console.error('Failed to refresh metric store:', e)
  process.exit(1)
})
