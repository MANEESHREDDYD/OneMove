import * as dotenv from 'dotenv'
import path from 'path'
import { createClient } from '@supabase/supabase-js'

const envPath = path.resolve(process.cwd(), '.env.local')
dotenv.config({ path: envPath })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

async function run() {
  if (!supabaseUrl || !supabaseServiceKey) {
    console.error('Missing Supabase env vars')
    process.exit(1)
  }

  const supabase = createClient(supabaseUrl, supabaseServiceKey)

  console.log('--- Seeding Experiments ---')
  
  // Create Experiment
  const { data: exp, error: expError } = await supabase.from('experiments').insert([{
    name: 'Dynamic Delivery Fee Test',
    description: 'Testing if dynamic delivery fees based on demand increases overall conversion vs flat fees.',
    status: 'ACTIVE'
  }]).select().single()

  if (expError) {
    console.error('Failed to create experiment:', expError)
    process.exit(1)
  }

  console.log(`✅ Created experiment: ${exp.name}`)

  // Create Variants
  await supabase.from('experiment_variants').insert([
    { experiment_id: exp.id, name: 'Control (Flat Fee)', description: '$3.99 Flat Fee', allocation_percentage: 50 },
    { experiment_id: exp.id, name: 'Treatment (Dynamic)', description: '$1.99 - $5.99 based on demand', allocation_percentage: 50 }
  ])

  console.log('✅ Created variants')
  console.log('✅ Seeding complete. Run `npm run experiments:simulate` now.')
}

run()
