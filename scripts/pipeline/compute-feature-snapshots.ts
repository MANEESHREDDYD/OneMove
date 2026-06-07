import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'

dotenv.config({ path: '.env.local' })

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

async function run() {
  console.log('--- STARTING FEATURE SNAPSHOTS ---')
  const { data: runData, error: runErr } = await supabaseAdmin.from('data_pipeline_runs').insert({
    pipeline_name: 'feature_snapshots',
    status: 'running'
  }).select('id').single()

  if (runErr) {
    console.error('Failed to start pipeline:', runErr)
    process.exit(1)
  }

  const runId = runData.id

  try {
    console.log('Computing ML feature snapshots...')
    
    // Simulate computing features
    await new Promise(r => setTimeout(r, 500))
    
    // Store global demand feature (just an example for Phase 1)
    await supabaseAdmin.from('metric_snapshots').insert({
      metric_name: 'global_demand_intensity',
      metric_value: Math.random() * 100, // Dummy feature
      dimensions: { region: 'all' }
    })

    await supabaseAdmin.from('data_pipeline_runs').update({
      status: 'success',
      end_time: new Date().toISOString(),
      rows_processed: 1
    }).eq('id', runId)

    console.log('--- FEATURE SNAPSHOTS SUCCESS ---')
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
