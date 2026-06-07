const { Client } = require('pg');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

const client = new Client({ connectionString: process.env.DIRECT_URL });
client.connect().then(async () => {
  await client.query("CREATE POLICY \"Users can insert partner_earnings\" ON public.partner_earnings FOR INSERT WITH CHECK (true);");
  console.log('Policies added for partner_earnings');
  process.exit(0);
}).catch(console.error);
