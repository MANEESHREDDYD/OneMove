import { createClient } from '@supabase/supabase-js'
import * as dotenv from 'dotenv'
import * as path from 'path'

// Load .env.local
dotenv.config({ path: path.resolve(process.cwd(), '.env.local') })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY

if (!supabaseUrl || !serviceRoleKey) {
  console.error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
  process.exit(1)
}

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: { autoRefreshToken: false, persistSession: false }
})

const USERS = [
  {
    // customer@onemove.demo
    id: '11111111-1111-1111-1111-111111111111',
    email: 'customer@onemove.demo',
    password: 'Demo@12345',
    user_metadata: { name: 'Demo Customer', role: 'customer' }
  },
  {
    // partner@onemove.demo
    id: '22222222-2222-2222-2222-222222222222',
    email: 'partner@onemove.demo',
    password: 'Demo@12345',
    user_metadata: { name: 'Demo Partner', role: 'driver' }
  },
  {
    // merchant@onemove.demo
    id: '33333333-3333-3333-3333-333333333333',
    email: 'merchant@onemove.demo',
    password: 'Demo@12345',
    user_metadata: { name: 'Demo Merchant', role: 'merchant' }
  },
  {
    // admin@onemove.demo
    id: '44444444-4444-4444-4444-444444444444',
    email: 'admin@onemove.demo',
    password: 'Demo@12345',
    user_metadata: { name: 'Demo Admin', role: 'admin' }
  }
]

async function seed() {
  console.log("Seeding Auth Users...")
  for (const u of USERS) {
    const { data, error } = await supabase.auth.admin.createUser({
      email: u.email,
      password: u.password,
      email_confirm: true,
      user_metadata: u.user_metadata
    })
    
    if (error) {
      console.log(`Failed to create ${u.email}:`, error.message)
    } else {
      console.log(`Created ${u.email} with ID ${data.user.id}`)
      
      // Update the ID to our hardcoded deterministic ID if supported, or we just rely on SQL seed updating the ID
      // Supabase createUser does not let you specify the ID directly in the JS client payload usually.
      // So instead, we will just print them out, or we use a SQL statement to fix the IDs.
      const newId = data.user.id
      
      // Force update the ID in auth.users via direct SQL update via supabase rpc or just leave it.
      // Actually, since we have the service role, let's just create the merchants linked to this new ID directly here!
      if (u.user_metadata.role === 'merchant') {
        const { error: mErr } = await supabase.from('merchants').insert({
          owner_id: newId,
          name: 'Demo Merchant Store',
          category: 'restaurant',
          status: 'active',
          address_line1: '123 Demo St',
          latitude: 40.7128,
          longitude: -74.0060
        })
        if (mErr) console.log("Failed to create merchant row:", mErr.message)
        else console.log("Created merchant row for", u.email)
      }
    }
  }
  console.log("Done.")
}

seed()
