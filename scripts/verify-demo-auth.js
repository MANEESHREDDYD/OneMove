const { createClient } = require('@supabase/supabase-js')
const path = require('path')
const fs = require('fs')

// Minimal dotenv parsing
const envPath = path.join(process.cwd(), '.env.local')
const envVars = {}

if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, 'utf-8').split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eqIdx = trimmed.indexOf('=')
    if (eqIdx === -1) continue
    const key = trimmed.substring(0, eqIdx).trim()
    const value = trimmed.substring(eqIdx + 1).trim()
    envVars[key] = value
  }
}

const supabaseUrl = envVars['NEXT_PUBLIC_SUPABASE_URL']
const serviceRoleKey = envVars['SUPABASE_SERVICE_ROLE_KEY']

if (!supabaseUrl || !serviceRoleKey) {
  console.error("Missing SUPABASE_SERVICE_ROLE_KEY or NEXT_PUBLIC_SUPABASE_URL in .env.local")
  process.exit(1)
}

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: { persistSession: false }
})

const REQUIRED_EMAILS = [
  'customer@onemove.demo',
  'partner@onemove.demo',
  'merchant@onemove.demo',
  'admin@onemove.demo'
]

async function verifyAuth() {
  console.log("Verifying Demo Auth Users...")
  let missing = 0

  for (const email of REQUIRED_EMAILS) {
    // The admin API requires pagination or user ID, we'll use a trick
    // to verify if a user exists by attempting a sign in (since we know the password)
    // Actually, we have service role key, we can list users.
    const { data: { users }, error } = await supabase.auth.admin.listUsers()
    
    if (error) {
      console.error("❌ Failed to fetch users from auth admin API:", error.message)
      process.exit(1)
    }

    const user = users.find(u => u.email === email)
    
    if (!user) {
      console.log(`❌ Missing Auth User: ${email}`)
      missing++
    } else {
      console.log(`✅ Found Auth User: ${email}`)
      
      // Check if profile exists
      const { data: profile, error: pErr } = await supabase.from('profiles').select('id, role').eq('id', user.id).single()
      if (pErr) {
         console.log(`  ❌ Missing public.profiles row for ${email}: ${pErr.message}`)
         missing++
      } else {
         console.log(`  ✅ Profile exists for ${email} with role ${profile.role}`)
      }
    }
  }

  if (missing > 0) {
    console.error(`\n❌ Auth verification failed. Missing required users or profiles.`)
    process.exit(1)
  }

  console.log("\n✅ All demo auth users verified successfully.")
  process.exit(0)
}

verifyAuth()
