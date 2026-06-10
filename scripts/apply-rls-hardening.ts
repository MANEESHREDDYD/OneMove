/**
 * Applies the final RLS hardening migration (supabase/fixes/2026_rls_hardening.sql)
 * to the database via DIRECT_URL. Idempotent — safe to re-run.
 *
 *   npm run db:harden-rls
 */
import { Client } from 'pg'
import * as path from 'path'
import * as fs from 'fs'

const envPath = path.join(process.cwd(), '.env.local')
const envVars: Record<string, string> = {}
if (fs.existsSync(envPath)) {
  for (const line of fs.readFileSync(envPath, 'utf-8').split('\n')) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq === -1) continue
    const key = trimmed.substring(0, eq).trim()
    let value = trimmed.substring(eq + 1).trim()
    if (value.startsWith('"') && value.endsWith('"')) value = value.slice(1, -1)
    envVars[key] = value
  }
}

const directUrl = envVars['DIRECT_URL']
if (!directUrl) {
  console.error('Missing DIRECT_URL in .env.local')
  process.exit(1)
}

async function run() {
  const file = 'supabase/fixes/2026_rls_hardening.sql'
  const sql = fs.readFileSync(path.join(process.cwd(), file), 'utf-8')
  const client = new Client({ connectionString: directUrl })
  await client.connect()
  try {
    await client.query(sql)
    console.log(`✅ Applied ${file} (profiles locked + safe display views).`)
  } catch (err) {
    console.error(`❌ Error applying ${file}:`, err)
    process.exitCode = 1
  } finally {
    await client.end()
  }
}

run().catch((err) => {
  console.error(err)
  process.exitCode = 1
})
