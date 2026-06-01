const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

const envPath = path.join(process.cwd(), '.env.local');
const envVars = {};
if (fs.existsSync(envPath)) {
  fs.readFileSync(envPath, 'utf-8').split('\n').forEach(line => {
    const t = line.trim();
    if (!t || t.startsWith('#')) return;
    const e = t.indexOf('=');
    if (e === -1) return;
    const key = t.substring(0, e).trim();
    let val = t.substring(e + 1).trim();
    if (val.startsWith('"') && val.endsWith('"')) val = val.slice(1, -1);
    envVars[key] = val;
  });
}

async function run() {
  const client = new Client({ connectionString: envVars.DIRECT_URL });
  await client.connect();

  // Soft-deleted rows still block unique constraint. Hard-delete them.
  // First clear identities
  try { 
    const r = await client.query("DELETE FROM auth.identities WHERE user_id IN (SELECT id FROM auth.users WHERE email LIKE '%demo%' AND deleted_at IS NOT NULL)"); 
    console.log("Deleted identities for soft-deleted demo users:", r.rowCount); 
  } catch(e) { console.log("identities:", e.message); }

  // Hard-delete soft-deleted demo users
  const r = await client.query("DELETE FROM auth.users WHERE email LIKE '%demo%' AND deleted_at IS NOT NULL");
  console.log("Hard-deleted soft-deleted demo users:", r.rowCount);

  // Also hard-delete any remaining
  const r2 = await client.query("DELETE FROM auth.users WHERE email LIKE '%demo%'");
  console.log("Hard-deleted remaining demo users:", r2.rowCount);

  // Also clean corresponding profiles  
  try { await client.query("DELETE FROM profiles WHERE id NOT IN (SELECT id FROM auth.users)"); } catch(e) {}

  // Verify
  const { rows } = await client.query("SELECT COUNT(*) FROM auth.users WHERE email LIKE '%demo%'");
  console.log("Remaining demo users:", rows[0].count);

  await client.end();
}

run().catch(e => { console.error(e); process.exit(1); });
