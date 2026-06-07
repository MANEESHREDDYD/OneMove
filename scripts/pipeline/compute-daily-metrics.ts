import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'
import { computeDailyMetrics } from '../../lib/metrics/computeMetrics'

dotenv.config({ path: '.env.local' })

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

async function run() {
  console.log('--- STARTING DAILY METRICS COMPUTATION ---')
  const { data, error } = await supabaseAdmin.from('data_pipeline_runs').insert({
    pipeline_name: 'compute_daily_metrics',
    status: 'running'
  }).select('id').single()

  if (error) {
    console.error('Failed to start pipeline:', error)
    process.exit(1)
  }

  const runId = data.id

  try {
    const today = new Date().toISOString().split('T')[0]
    console.log(`Computing metrics for date: ${today}`)
    
    const result = await computeDailyMetrics(supabaseAdmin, today)
    
    console.log(`Metrics computed. GMV: $${result.gmv}, Total Orders: ${result.totalOrders}`)

    await supabaseAdmin.from('data_pipeline_runs').update({
      status: 'success',
      end_time: new Date().toISOString(),
      rows_processed: result.totalOrders
    }).eq('id', runId)

    console.log('--- DAILY METRICS SUCCESS ---')
  } catch (err: any) {
    console.error('Pipeline Error:', err)
    await supabaseAdmin.from('data_pipeline_runs').update({
      status: 'failed',
      end_time: new Date().toISOString(),
      error_message: err.message
    }).eq('id', runId)
    process.exit(1)
  }
}

run()
