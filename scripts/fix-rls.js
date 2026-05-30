/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('fs')
const path = require('path')

const file = path.join(__dirname, '../supabase/policies.sql')
let sql = fs.readFileSync(file, 'utf8')

// If they are not already fixed, drop old and create new
if (sql.includes('CREATE POLICY "Public profiles are viewable by everyone." ON profiles')) {
  sql = sql.replace(
    'CREATE POLICY "Public profiles are viewable by everyone." ON profiles FOR SELECT USING (true);',
    `DROP POLICY IF EXISTS "Public profiles are viewable by everyone." ON profiles;\nCREATE POLICY "Profiles are viewable by authenticated users." ON profiles FOR SELECT USING (auth.role() = 'authenticated');`
  )
}

if (sql.includes('CREATE POLICY "Merchants are viewable by everyone." ON merchants')) {
  sql = sql.replace(
    'CREATE POLICY "Merchants are viewable by everyone." ON merchants FOR SELECT USING (true);',
    `DROP POLICY IF EXISTS "Merchants are viewable by everyone." ON merchants;\nCREATE POLICY "Merchants are viewable by authenticated users." ON merchants FOR SELECT USING (auth.role() = 'authenticated');`
  )
}

if (sql.includes('CREATE POLICY "Products are viewable by everyone." ON products')) {
  sql = sql.replace(
    'CREATE POLICY "Products are viewable by everyone." ON products FOR SELECT USING (true);',
    `DROP POLICY IF EXISTS "Products are viewable by everyone." ON products;\nCREATE POLICY "Products are viewable by authenticated users." ON products FOR SELECT USING (auth.role() = 'authenticated');`
  )
}

fs.writeFileSync(file, sql)
console.log("Updated policies.sql with stricter RLS.")

