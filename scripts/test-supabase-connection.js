/* eslint-disable @typescript-eslint/no-unused-vars */
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

async function testConnection() {
  console.log("Testing connection to Supabase...")
  
  // Query a table that should exist if schema.sql is applied
  const { data, error } = await supabase.from('profiles').select('id').limit(1)
  
  if (error) {
    if (error.code === '42P01' || error.message.includes('Could not find the table')) {
      console.error("\n❌ Supabase connection works, but database schema has not been applied yet.")
      console.error("Please apply the SQL files in Supabase dashboard as per docs/SUPABASE_SETUP.md.")
      process.exit(1)
    }
    console.error("\n❌ Connection failed:", error.message)
    process.exit(1)
  }
  
  console.log("\n✅ Connection successful! The database schema is applied.")
  process.exit(0)
}

testConnection()
