import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'

dotenv.config({ path: '.env.local' })

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

async function run() {
  console.log('--- STARTING DATA QUALITY CHECKS ---')
  const { data: runData, error: runErr } = await supabaseAdmin.from('data_pipeline_runs').insert({
    pipeline_name: 'data_quality_checks',
    status: 'running'
  }).select('id').single()

  if (runErr) {
    console.error('Failed to start pipeline:', runErr)
    process.exit(1)
  }

  const runId = runData.id

  try {
    const checks = [
      {
        name: 'Orders missing customer_id',
        severity: 'high',
        affected_table: 'orders',
        recommended_fix: 'Ensure all creation pathways inject auth.uid() into customer_id.',
        query: supabaseAdmin.from('orders').select('id, created_at').is('customer_id', null)
      },
      {
        name: 'Eats/Grocery orders missing merchant_id',
        severity: 'critical',
        affected_table: 'orders',
        recommended_fix: 'Check checkout flow to ensure merchant_id is passed.',
        query: supabaseAdmin.from('orders').select('id').in('service_type', ['eats', 'grocery']).is('merchant_id', null)
      },
      {
        name: 'Negative total amounts',
        severity: 'high',
        affected_table: 'orders',
        recommended_fix: 'Add database CHECK constraint for total_amount >= 0.',
        query: supabaseAdmin.from('orders').select('id, total_amount').lt('total_amount', 0)
      },
      {
        name: 'Missing location metadata for rides/courier',
        severity: 'high',
        affected_table: 'orders',
        recommended_fix: 'Ensure pickup_location and dropoff_location JSONB is complete.',
        query: supabaseAdmin.from('orders').select('id').in('service_type', ['ride', 'courier']).or('pickup_location.is.null,dropoff_location.is.null')
      }
      // Add more checks as needed...
    ]

    let totalFailedRecords = 0

    for (const check of checks) {
      console.log(`Running check: ${check.name}...`)
      const { data, error } = await check.query
      
      if (error) {
        console.error(`Error running check ${check.name}:`, error)
        continue
      }

      const failedCount = data.length
      totalFailedRecords += failedCount

      const status = failedCount === 0 ? 'pass' : (check.severity === 'critical' ? 'fail' : 'warning')
      
      await supabaseAdmin.from('data_quality_results').insert({
        run_id: runId,
        check_name: check.name,
        status,
        failed_rows_count: failedCount,
        sample_failed_records: data.slice(0, 5),
        severity: check.severity,
        affected_table: check.affected_table,
        recommended_fix: check.recommended_fix
      })
      
      console.log(`Check ${check.name}: ${status.toUpperCase()} (${failedCount} failures)`)
    }

    await supabaseAdmin.from('data_pipeline_runs').update({
      status: 'success',
      end_time: new Date().toISOString(),
      rows_processed: checks.length
    }).eq('id', runId)

    console.log(`--- DATA QUALITY CHECKS SUCCESS (${totalFailedRecords} issues found) ---`)
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
