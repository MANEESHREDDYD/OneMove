const fs = require('fs')
const path = require('path')
const { Client } = require('pg')

// Load environment variables manually without relying on dotenv
function loadEnv() {
  const envPath = path.resolve(process.cwd(), '.env.local')
  if (!fs.existsSync(envPath)) {
    console.error(`ERROR: Could not find .env.local at ${envPath}`)
    process.exit(1)
  }

  const envContent = fs.readFileSync(envPath, 'utf8')
  const envVars = {}
  
  envContent.split('\n').forEach(line => {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) return
    
    const match = trimmed.match(/^([^=]+)=(.*)$/)
    if (match) {
      const key = match[1].trim()
      let value = match[2].trim()
      // Remove quotes if present
      if ((value.startsWith('"') && value.endsWith('"')) || 
          (value.startsWith("'") && value.endsWith("'"))) {
        value = value.substring(1, value.length - 1)
      }
      envVars[key] = value
      process.env[key] = value
    }
  })
  
  return envVars
}

async function patchPhase4() {
  console.log('--- Applying Phase 4 Patch ---')
  
  loadEnv()
  
  let dbUrl = process.env.DATABASE_URL
  if (!dbUrl) {
    console.error('ERROR: DATABASE_URL not found in .env.local')
    process.exit(1)
  }

  // Handle Supabase transaction connection string format (port 6543)
  if (dbUrl.includes(':6543')) {
    dbUrl = dbUrl.replace(':6543', ':5432')
    console.log('Note: Replaced port 6543 with 5432 for session mode connection.')
  }

  const client = new Client({
    connectionString: dbUrl,
    ssl: { rejectUnauthorized: false }
  })

  try {
    await client.connect()
    console.log('Connected to database.')
    
    // Patch Support Tickets
    console.log('Patching support_tickets table...')
    await client.query(`
      ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS category text DEFAULT 'general';
      ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS priority text DEFAULT 'LOW';
      ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS assistant_explanation text;
      ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS recommended_action text;
      ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS refund_eligibility boolean DEFAULT false;
      ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS escalation_required boolean DEFAULT false;
    `)
    
    console.log('Reloading PostgREST schema cache...')
    await client.query('NOTIFY pgrst, reload_schema;')
    
    console.log('✅ Patch applied successfully.')
  } catch (err) {
    console.error('❌ Failed to patch schema:', err)
    process.exit(1)
  } finally {
    await client.end()
  }
}

patchPhase4()
