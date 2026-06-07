const { Client } = require('pg');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

const client = new Client({ connectionString: process.env.DIRECT_URL });
client.connect().then(async () => {
  const res = await client.query("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'order_status'");
  console.table(res.rows);
  process.exit(0);
}).catch(console.error);
