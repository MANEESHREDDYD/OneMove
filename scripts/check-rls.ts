import { Client } from 'pg';
import * as path from 'path';
import * as fs from 'fs';

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
    if (value.startsWith('"') && value.endsWith('"')) value = value.substring(1, value.length - 1);
    envVars[key] = value;
  }
}

async function run() {
  const client = new Client({ connectionString: envVars['DIRECT_URL'] });
  await client.connect();
  const { rows } = await client.query(`SELECT * FROM pg_policies WHERE tablename IN ('merchants', 'products', 'orders')`);
  console.log("RLS Policies:");
  rows.forEach(r => console.log(`[${r.tablename}] ${r.policyname} (${r.cmd}): ${r.qual} | ${r.with_check}`));
  await client.end();
}

run().catch(console.error);
