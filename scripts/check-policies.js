const { Client } = require('pg');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

const client = new Client({ connectionString: process.env.DIRECT_URL });
client.connect().then(async () => {
  const res = await client.query("select policyname, cmd from pg_policies where tablename = 'orders'");
  console.table(res.rows);
  process.exit(0);
}).catch(console.error);
