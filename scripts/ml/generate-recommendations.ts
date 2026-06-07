import { createClient } from '@supabase/supabase-js'
import { generateRecommendations } from '../../lib/ml/recommendations'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

async function main() {
  console.log('--- Running Customer Recommendations Engine ---')

  const { data: customers, error } = await supabase
    .from('profiles')
    .select('id')
    .eq('role', 'customer')

  if (error) {
    console.error('Error fetching customers:', error)
    process.exit(1)
  }

  if (!customers) {
    console.log('No customers found.')
    process.exit(0)
  }

  for (const customer of customers) {
    await generateRecommendations(customer.id)
  }

  console.log(`✅ Successfully generated recommendations for ${customers.length} customers.`)
  process.exit(0)
}

main().catch(err => {
  console.error('Pipeline failed:', err)
  process.exit(1)
})
