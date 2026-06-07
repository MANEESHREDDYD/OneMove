import * as dotenv from 'dotenv'
import path from 'path'
import { runAdminOpsAssistant } from '../../lib/ai/adminOpsAssistant'

const envPath = path.resolve(process.cwd(), '.env.local')
dotenv.config({ path: envPath })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

async function run() {
  if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Missing Supabase env vars')
    process.exit(1)
  }

  console.log('--- Running Admin Ops Assistant ---')
  try {
    const result = await runAdminOpsAssistant(supabaseUrl, supabaseServiceKey)
    console.log(`✅ ${result.message}`)
  } catch (err: any) {
    console.error('❌ Ops Insights generation failed:', err.message)
    process.exit(1)
  }
}

run()
