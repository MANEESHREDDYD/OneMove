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
  -- Profiles
  DROP POLICY IF EXISTS "Public profiles are viewable by everyone." ON profiles;
  DROP POLICY IF EXISTS "Profiles are viewable by authenticated users." ON profiles;
  DROP POLICY IF EXISTS "Users can view own profile." ON profiles;
  CREATE POLICY "Users can view own profile." ON profiles FOR SELECT USING (auth.uid() = id);

  -- Merchants
  DROP POLICY IF EXISTS "Merchants are viewable by everyone." ON merchants;
  DROP POLICY IF EXISTS "Merchants are viewable by authenticated users." ON merchants;
  DROP POLICY IF EXISTS "Merchant owners can view their merchants." ON merchants;
  CREATE POLICY "Merchant owners can view their merchants." ON merchants FOR SELECT USING (auth.uid() = owner_id);

  -- Products
  DROP POLICY IF EXISTS "Products are viewable by everyone." ON products;
  DROP POLICY IF EXISTS "Products are viewable by authenticated users." ON products;
  DROP POLICY IF EXISTS "Merchant owners can view their products." ON products;
  CREATE POLICY "Merchant owners can view their products." ON products FOR SELECT USING (
    EXISTS (SELECT 1 FROM merchants m WHERE m.id = products.merchant_id AND m.owner_id = auth.uid())
  );
  `;

  await client.query(sql);
  console.log("Applied strictest RLS policies.");

  await client.end();
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});

