const { Client } = require('pg');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

const client = new Client({ connectionString: process.env.DIRECT_URL });
client.connect().then(async () => {
  const res = await client.query("SELECT id, status, driver_id, created_at FROM orders WHERE status = 'accepted' ORDER BY created_at DESC LIMIT 5");
  console.table(res.rows);
  
  const res2 = await client.query("SELECT id, status, driver_id, service_type FROM orders ORDER BY created_at DESC LIMIT 5");
  console.table(res2.rows);

  process.exit(0);
}).catch(console.error);
