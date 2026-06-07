const { Client } = require('pg');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

const client = new Client({ connectionString: process.env.DIRECT_URL });
client.connect().then(async () => {
  await client.query("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'assigned'");
  await client.query("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'partner_assigned'");
  await client.query("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'delivered'");
  await client.query("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'refunded'");
  console.log('Enums added');
  process.exit(0);
}).catch(console.error);
