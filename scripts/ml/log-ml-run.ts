import * as dotenv from 'dotenv'
import path from 'path'
import { createClient } from '@supabase/supabase-js'

const envPath = path.resolve(process.cwd(), '.env.local')
dotenv.config({ path: envPath })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

export async function logMlRun(
  supabase: any,
  runName: string,
  modelFamily: string,
  modelVersion: string,
  status: string,
  startTime: Date,
  endTime: Date,
  inputRows: number,
  outputRows: number,
  errors: number = 0
) {
  const duration = endTime.getTime() - startTime.getTime()
  
  const { error } = await supabase.from('ml_pipeline_runs').insert([{
    run_name: runName,
    model_family: modelFamily,
    model_version: modelVersion,
    status: status,
    started_at: startTime.toISOString(),
    ended_at: endTime.toISOString(),
    duration_ms: duration,
    input_row_count: inputRows,
    output_row_count: outputRows,
    error_count: errors
  }])

  if (error) {
    console.error(`Failed to log ML run ${runName}:`, error.message)
  }
}

async function run() {
  if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Missing Supabase env vars')
    process.exit(1)
  }

  const supabase = createClient(supabaseUrl, supabaseServiceKey)

  console.log('--- MLOps Pipeline Report ---')
  const { data, error } = await supabase
    .from('ml_pipeline_runs')
    .select('*')
    .order('started_at', { ascending: false })
    .limit(10)

  if (error) {
    console.error('Failed to fetch runs:', error.message)
    process.exit(1)
  }

  if (!data || data.length === 0) {
    console.log('No ML pipeline runs found. You should run `npm run ml:score-all`')
  } else {
    console.table(data.map(r => ({
      Run: r.run_name,
      Family: r.model_family,
      Status: r.status,
      Duration: `${r.duration_ms}ms`,
      OutputRows: r.output_row_count
    })))
  }
}

// Only execute if run directly
if (require.main === module) {
  run()
}
