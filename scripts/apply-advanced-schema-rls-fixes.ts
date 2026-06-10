 
import { Client } from 'pg';
import * as path from 'path';
import * as fs from 'fs';

// Minimal dotenv parsing
const envPath = path.join(process.cwd(), '.env.local');
const envVars: Record<string, string> = {};

if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.substring(0, eqIdx).trim();
    let value = trimmed.substring(eqIdx + 1).trim();
    if (value.startsWith('"') && value.endsWith('"')) {
      value = value.substring(1, value.length - 1);
    }
    envVars[key] = value;
  }
}

const directUrl = envVars['DIRECT_URL'];

if (!directUrl) {
  console.error("Missing DIRECT_URL in .env.local");
  process.exit(1);
}

const client = new Client({ connectionString: directUrl });

async function run() {
  await client.connect();
  console.log("✅ Connected to database.");

  const files = [
    'supabase/fixes/2026_advanced_qa_schema_fixes.sql',
    'supabase/fixes/2026_advanced_qa_rls_fixes.sql',
    'supabase/fixes/2026_admin_metrics_rpc.sql',
    'supabase/fixes/2026_rls_hardening.sql'
  ];

  for (const file of files) {
    const filePath = path.join(process.cwd(), file);
    if (!fs.existsSync(filePath)) {
      console.warn(`⚠️ File not found: ${file}`);
      continue;
    }
    
    console.log(`\n⏳ Applying ${file}...`);
    const sql = fs.readFileSync(filePath, 'utf-8');
    
    try {
      await client.query(sql);
      console.log(`✅ Successfully applied ${file}`);
    } catch (err) {
      console.error(`❌ Error applying ${file}:`);
      console.error(err);
      process.exit(1);
    }
  }

  console.log("\n🎉 All fixes applied successfully.");
  await client.end();
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
