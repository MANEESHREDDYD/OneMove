import { Client } from 'pg';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

async function debugSchemaContract() {
  const client = new Client({ connectionString: process.env.DIRECT_URL });
  await client.connect();

  console.log('======================================================================');
  console.log('DEBUG: SCHEMA CONTRACT & RELATIONSHIPS');
  console.log('======================================================================\n');

  try {
    // Get all tables
    const { rows: tables } = await client.query(`
      SELECT tablename FROM pg_catalog.pg_tables
      WHERE schemaname = 'public';
    `);
    console.log('--- TABLES ---');
    tables.forEach(t => console.log(`- ${t.tablename}`));
    console.log('\n');

    // Get specific table columns
    const tablesToCheck = ['orders', 'rides', 'courier_jobs', 'payments', 'profiles', 'merchants', 'vehicles'];
    
    for (const table of tablesToCheck) {
      if (!tables.some(t => t.tablename === table)) continue;
      
      const { rows: cols } = await client.query(`
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = $1
      `, [table]);
      
      console.log(`--- ${table.toUpperCase()} COLUMNS ---`);
      cols.forEach(c => console.log(`  ${c.column_name} (${c.data_type}) ${c.is_nullable === 'YES' ? 'NULL' : 'NOT NULL'}`));
      console.log();
    }

    // Get Foreign Keys
    const { rows: fks } = await client.query(`
      SELECT
        tc.table_name, kcu.column_name,
        ccu.table_name AS foreign_table_name,
        ccu.column_name AS foreign_column_name
      FROM information_schema.table_constraints AS tc
      JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
      JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
      WHERE constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
    `);
    
    console.log('--- FOREIGN KEYS ---');
    fks.forEach(fk => {
      console.log(`- ${fk.table_name}.${fk.column_name} -> ${fk.foreign_table_name}.${fk.foreign_column_name}`);
    });
    console.log('\n');

    // Get RLS Policies
    const { rows: policies } = await client.query(`
      SELECT tablename, policyname, permissive, roles, cmd, qual, with_check 
      FROM pg_policies 
      WHERE schemaname = 'public'
    `);
    
    console.log('--- RLS POLICIES ---');
    if (policies.length === 0) console.log('No RLS policies found.');
    policies.forEach(p => {
      console.log(`Table: ${p.tablename} | Action: ${p.cmd} | Policy: ${p.policyname}`);
      console.log(`  Roles: ${p.roles}`);
      console.log(`  USING: ${p.qual}`);
      if (p.with_check) console.log(`  WITH CHECK: ${p.with_check}`);
    });

  } catch (error) {
    console.error('Error debugging schema:', error);
  } finally {
    await client.end();
  }
}

debugSchemaContract().catch(console.error);
