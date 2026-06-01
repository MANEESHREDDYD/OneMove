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

const directUrl = envVars['DIRECT_URL'];
if (!directUrl) { console.error("Missing DIRECT_URL"); process.exit(1); }

async function run() {
  const client = new Client({ connectionString: directUrl });
  await client.connect();

  const queries = [
    // Drop restrictive policies
    `DROP POLICY IF EXISTS "Merchant owners can view their merchants." ON merchants;`,
    `DROP POLICY IF EXISTS "Merchant owners can view their products." ON products;`,
    `DROP POLICY IF EXISTS "Merchants are viewable by everyone." ON merchants;`,
    `DROP POLICY IF EXISTS "Products are viewable by everyone." ON products;`,
    `DROP POLICY IF EXISTS "Merchants are viewable by authenticated users." ON merchants;`,
    `DROP POLICY IF EXISTS "Products are viewable by authenticated users." ON products;`,
    `DROP POLICY IF EXISTS "Users can view their own orders." ON orders;`,
    `DROP POLICY IF EXISTS "Involved parties can update orders." ON orders;`,
    `DROP POLICY IF EXISTS "Merchant owners can view their orders." ON orders;`,

    // Merchants visibility
    `CREATE POLICY "Merchants are viewable by authenticated users." ON merchants FOR SELECT USING (auth.role() = 'authenticated');`,
    
    // Products visibility
    `CREATE POLICY "Products are viewable by authenticated users." ON products FOR SELECT USING (auth.role() = 'authenticated');`,
    
    // Orders visibility (Customers, Drivers, Merchants, and available jobs)
    `CREATE POLICY "Users can view relevant orders." ON orders FOR SELECT USING (
      auth.uid() = customer_id OR 
      auth.uid() = driver_id OR 
      EXISTS (SELECT 1 FROM merchants m WHERE m.id = orders.merchant_id AND m.owner_id = auth.uid()) OR
      (driver_id IS NULL AND status IN ('pending', 'ready'))
    );`,
    
    // Orders update (Customers, Drivers, Merchants, and claiming jobs)
    `CREATE POLICY "Involved parties can update orders." ON orders FOR UPDATE USING (
      auth.uid() = customer_id OR 
      auth.uid() = driver_id OR 
      EXISTS (SELECT 1 FROM merchants m WHERE m.id = orders.merchant_id AND m.owner_id = auth.uid()) OR
      (driver_id IS NULL AND status IN ('pending', 'ready'))
    );`
  ];

  console.log("Applying scoped RLS policies...");
  for (const q of queries) {
    try {
      await client.query(q);
      console.log(`✅ Applied: ${q.substring(0, 50)}...`);
    } catch (e: any) {
      console.error(`❌ Error applying: ${q}\n  -> ${e.message}`);
    }
  }

  await client.end();
  console.log("Done.");
}

run().catch(console.error);
