import * as dotenv from 'dotenv'
import path from 'path'
import { simulateExperiments } from '../../lib/experiments/experimentEngine'

const envPath = path.resolve(process.cwd(), '.env.local')
dotenv.config({ path: envPath })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

async function run() {
  if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Missing Supabase env vars')
    process.exit(1)
  }

  console.log('--- Running Experiment Simulation Engine ---')
  try {
    await simulateExperiments(supabaseUrl, supabaseServiceKey)
    console.log('✅ Successfully simulated active experiments')
  } catch (err: any) {
    console.error('❌ Experiment simulation failed:', err.message)
    process.exit(1)
  }
}

run()
