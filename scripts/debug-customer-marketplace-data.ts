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

  console.log("=== CUSTOMER MARKETPLACE DEBUG ===");
  
  const { rows: users } = await client.query(`
    SELECT p.id as profile_id, p.id as auth_user_id, p.role
    FROM profiles p
    JOIN auth.users u ON u.id = p.id
    WHERE u.email = 'customer@onemove.demo'
  `);
  
  const user = users[0];
  if (!user) {
    console.log("customer@onemove.demo not found!");
  } else {
    console.log(`Current customer demo user:`);
    console.log(`- auth_user_id: ${user.auth_user_id}`);
    console.log(`- profile_id: ${user.profile_id}`);
    console.log(`- role: ${user.role}`);
    
    const { rows: orderCounts } = await client.query(`SELECT service_type, count(*) as count FROM orders WHERE customer_id = $1 GROUP BY service_type`, [user.auth_user_id]);
    console.log("- customer orders count:", orderCounts);
  }

  console.log("\nGrocery:");
  const { rows: groceryMerchants } = await client.query(`SELECT count(*) as count FROM merchants WHERE category = 'grocery'`);
  const { rows: groceryProducts } = await client.query(`SELECT count(*) as count FROM products WHERE category IN ('Produce', 'Dairy & Eggs', 'Bakery', 'Snacks', 'Beverages')`);
  const { rows: groceryLinked } = await client.query(`
    SELECT count(p.id) as count 
    FROM products p 
    JOIN merchants m ON p.merchant_id = m.id 
    WHERE m.category = 'grocery'
  `);
  console.log(`- grocery merchants count: ${groceryMerchants[0].count}`);
  console.log(`- grocery products count: ${groceryProducts[0].count}`);
  console.log(`- products linked to merchant count: ${groceryLinked[0].count}`);
  console.log(`- query used by /customer/grocery: supabase.from('merchants').select('*').eq('category', 'grocery')`);
  
  console.log("\nEats:");
  const { rows: eatsMerchants } = await client.query(`SELECT count(*) as count FROM merchants WHERE category = 'restaurant'`);
  const { rows: eatsProducts } = await client.query(`
    SELECT count(p.id) as count 
    FROM products p 
    JOIN merchants m ON p.merchant_id = m.id 
    WHERE m.category = 'restaurant'
  `);
  console.log(`- restaurant merchants count: ${eatsMerchants[0].count}`);
  console.log(`- food menu items count: ${eatsProducts[0].count}`);
  console.log(`- items linked to merchant count: ${eatsProducts[0].count}`);
  console.log(`- query used by /customer/eats: supabase.from('merchants').select('*').eq('category', 'restaurant')`);
  
  console.log("\nOrders:");
  const { rows: allOrders } = await client.query(`SELECT service_type, count(*) FROM orders GROUP BY service_type`);
  console.log("- orders breakdown:");
  console.log(allOrders);

  await client.end();
}

run().catch(console.error);
