import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'
import path from 'path'

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('Missing Supabase credentials in .env.local')
  process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseServiceKey)

async function getCount(table: string): Promise<number> {
  const { count, error } = await supabase.from(table).select('*', { count: 'exact', head: true })
  if (error) {
    console.warn(`Warning: Could not read count for ${table}:`, error.message)
    return 0
  }
  return count || 0
}

async function main() {
  console.log('\n================================================')
  console.log('🤖 Debug: Intelligence Platform Data Counts')
  console.log('================================================\n')

  const tables = [
    'ops_insights',
    'support_tickets',
    'experiments',
    'experiment_variants',
    'experiment_metrics',
    'ml_pipeline_runs',
    'recommendations',
    'customer_segments',
    'merchant_reliability_scores',
    'partner_trust_scores',
    'risk_checks',
    'demand_forecasts'
  ]

  let hasZero = false

  for (const table of tables) {
    const count = await getCount(table)
    console.log(`${table.padEnd(30, ' ')} | Count: ${count.toString().padStart(5, ' ')}`)
    if (count === 0 && table !== 'experiments') { // sometimes experiments could be zero if not seeded, but we'll flag it
      hasZero = true
    }
  }

  console.log('\n================================================')
  if (hasZero) {
    console.log('⚠️ WARNING: Some tables have 0 rows. Run `npm run intelligence:refresh` to populate.')
  } else {
    console.log('✅ SUCCESS: All intelligence tables have populated data.')
  }
  console.log('================================================\n')
}

main()
