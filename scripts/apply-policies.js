/* eslint-disable @typescript-eslint/no-require-imports */
const { Client } = require('pg');
require('dotenv').config({ path: '.env.local' });

async function run() {
  const connectionString = process.env.DIRECT_URL;
  if (!connectionString) {
    console.error("Missing DIRECT_URL");
    process.exit(1);
  }

  const client = new Client({ connectionString });
  await client.connect();
  console.log("Connected to DB.");

  const sql = `
  DROP POLICY IF EXISTS "Public profiles are viewable by everyone." ON profiles;
  DROP POLICY IF EXISTS "Profiles are viewable by authenticated users." ON profiles;
  CREATE POLICY "Profiles are viewable by authenticated users." ON profiles FOR SELECT USING (auth.role() = 'authenticated');

  DROP POLICY IF EXISTS "Merchants are viewable by everyone." ON merchants;
  DROP POLICY IF EXISTS "Merchants are viewable by authenticated users." ON merchants;
  CREATE POLICY "Merchants are viewable by authenticated users." ON merchants FOR SELECT USING (auth.role() = 'authenticated');

  DROP POLICY IF EXISTS "Products are viewable by everyone." ON products;
  DROP POLICY IF EXISTS "Products are viewable by authenticated users." ON products;
  CREATE POLICY "Products are viewable by authenticated users." ON products FOR SELECT USING (auth.role() = 'authenticated');
  `;

  await client.query(sql);
  console.log("Applied stricter RLS policies.");

  await client.end();
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});

