import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import path from 'path'

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('Missing Supabase credentials in .env.local')
  process.exit(1)
}

const supabase = createClient(supabaseUrl, supabaseServiceKey)

async function debugPartnerJobs() {
  console.log('=== Partner Jobs QA Audit ===')
  
  const { data: partnerUsers } = await supabase.from('profiles').select('*').eq('role', 'driver').limit(5)
  if (!partnerUsers || partnerUsers.length === 0) {
    console.error('❌ No partner users found.')
    process.exit(1)
  }

  console.log(`✅ Found ${partnerUsers.length} partner users.`)

  const { data: availableJobs, error: jobsError } = await supabase
    .from('orders')
    .select('*')
    .in('status', ['pending', 'ready', 'requested', 'created'])
    .is('driver_id', null)

  if (jobsError) {
    console.error('❌ Error fetching jobs:', jobsError)
  } else {
    console.log(`✅ Found ${availableJobs.length} available jobs for partners.`)
    const breakdown = availableJobs.reduce((acc: any, job) => {
      acc[job.service_type] = (acc[job.service_type] || 0) + 1
      return acc
    }, {})
    console.table(breakdown)
  }

  const { data: activeJobs, error: activeError } = await supabase
    .from('orders')
    .select('*')
    .not('driver_id', 'is', null)
    .in('status', ['accepted', 'in_transit', 'arrived', 'started', 'picked_up'])

  if (activeError) {
    console.error('❌ Error fetching active jobs:', activeError)
  } else {
    console.log(`✅ Found ${activeJobs.length} active jobs assigned to partners.`)
  }

  console.log('=== Partner QA Complete ===')
}

debugPartnerJobs().catch(console.error)
