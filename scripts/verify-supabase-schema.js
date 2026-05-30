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
const anonKey = envVars['NEXT_PUBLIC_SUPABASE_ANON_KEY']

if (!supabaseUrl || !anonKey) {
  console.error("Missing Supabase credentials in .env.local")
  process.exit(1)
}

const supabase = createClient(supabaseUrl, anonKey, {
  auth: { persistSession: false }
})

const REQUIRED_TABLES = [
  'profiles',
  'merchants',
  'products',
  'vehicles',
  'orders',
  'order_items',
  'payments',
  'tracking'
]

async function verify() {
  console.log("Verifying Supabase schema tables...")
  let missing = 0

  for (const table of REQUIRED_TABLES) {
    const { error } = await supabase.from(table).select('id').limit(1)
    
    if (error && (error.code === '42P01' || error.message.includes('Could not find the table'))) {
      console.log(`❌ Table missing: ${table}`)
      missing++
    } else if (error) {
      console.log(`⚠️ Error accessing ${table}: ${error.message}`)
    } else {
      console.log(`✅ Table exists: ${table}`)
    }
  }

  if (missing > 0) {
    console.error(`\n❌ Schema verification failed. ${missing} required tables are missing.`)
    process.exit(1)
  }

  console.log("\n✅ All required tables verified successfully.")
  process.exit(0)
}

verify()
