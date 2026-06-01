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

  // Check if there's a deleted_at or is_deleted column  
  const { rows: cols } = await client.query(
    "SELECT column_name FROM information_schema.columns WHERE table_schema='auth' AND table_name='users' ORDER BY ordinal_position"
  );
  console.log("auth.users columns:", cols.map(c => c.column_name).join(', '));

  // Check for merchant_demo_0 specifically
  const { rows } = await client.query(
    "SELECT id, email, deleted_at FROM auth.users WHERE email = 'merchant_demo_0@example.com'"
  );
  console.log("\nmerchant_demo_0:", rows.length ? JSON.stringify(rows[0]) : "NOT FOUND");

  // Check total with that pattern including soft-deleted
  const { rows: all } = await client.query(
    "SELECT COUNT(*) as total FROM auth.users WHERE email LIKE '%demo%'"
  );
  console.log("Total demo users (including soft-deleted):", all[0].total);

  await client.end();
}

run().catch(e => { console.error(e); process.exit(1); });
