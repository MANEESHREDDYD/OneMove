import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'

dotenv.config({ path: '.env.local' })

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

async function run() {
  console.log('--- STARTING EVENT INGESTION ---')
  const { data, error } = await supabase.from('data_pipeline_runs').insert({
    pipeline_name: 'ingest_events',
    status: 'running'
  }).select('id').single()

  if (error) {
    console.error('Failed to start pipeline:', error)
    process.exit(1)
  }

  const runId = data.id

  try {
    // In a real system, this would pull from Kafka/Kinesis and insert into a raw events table
    // For this portfolio MVP, we'll just log that it checked for new events.
    console.log('Ingesting realtime events from marketplace...')
    
    // Simulate some work
    await new Promise(r => setTimeout(r, 1000))
    
    // Count how many orders were created today
    const startOfDay = new Date()
    startOfDay.setUTCHours(0, 0, 0, 0)
    
    const { count } = await supabase.from('orders').select('*', { count: 'exact', head: true }).gte('created_at', startOfDay.toISOString())
    
    console.log(`Processed ${count || 0} raw events today.`)

    await supabase.from('data_pipeline_runs').update({
      status: 'success',
      end_time: new Date().toISOString(),
      rows_processed: count || 0
    }).eq('id', runId)

    console.log('--- EVENT INGESTION SUCCESS ---')
  } catch (err: any) {
    console.error('Pipeline Error:', err)
    await supabase.from('data_pipeline_runs').update({
      status: 'failed',
      end_time: new Date().toISOString(),
      error_message: err.message
    }).eq('id', runId)
    process.exit(1)
  }
}

run()
