/* eslint-disable @typescript-eslint/no-require-imports */
const { Client } = require('pg')
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
    let value = trimmed.substring(eqIdx + 1).trim()
    if (value.startsWith('"') && value.endsWith('"')) {
      value = value.substring(1, value.length - 1)
    }
    envVars[key] = value
  }
}

const directUrl = envVars['DIRECT_URL']

if (!directUrl) {
  console.error("Missing DIRECT_URL in .env.local")
  process.exit(1)
}

const client = new Client({
  connectionString: directUrl
})

const SQL_FILES = [
  'supabase/updates.sql',
  'supabase/indexes.sql',
  'supabase/seed.sql'
]

async function runSQL() {
  try {
    await client.connect()
    console.log("✅ Connected to Supabase via Postgres DIRECT_URL")

    for (const file of SQL_FILES) {
      const filePath = path.join(process.cwd(), file)
      if (!fs.existsSync(filePath)) {
        console.warn(`⚠️ Skipping ${file} - file not found`)
        continue
      }

      console.log(`Executing ${file}...`)
      const sql = fs.readFileSync(filePath, 'utf-8')
      
      try {
        await client.query(sql)
        console.log(`✅ Successfully applied ${file}`)
      } catch (err) {
        console.error(`\n❌ Error applying ${file}:`)
        console.error(`Message: ${err.message}`)
        console.error(`Position: ${err.position || 'Unknown'}`)
        process.exit(1)
      }
    }

    console.log("\n✅ All SQL files applied successfully!")
    process.exit(0)
  } catch (err) {
    console.error("❌ Connection or Execution error:", err.message)
    process.exit(1)
  } finally {
    await client.end()
  }
}

runSQL()
