const { Client } = require('pg');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

const client = new Client({ connectionString: process.env.DIRECT_URL });
client.connect().then(async () => {
  await client.query("CREATE POLICY \"Users can insert order_events\" ON public.order_status_events FOR INSERT WITH CHECK (true);");
  await client.query("CREATE POLICY \"Users can insert analytics\" ON public.analytics_events FOR INSERT WITH CHECK (true);");
  console.log('Policies added');
  process.exit(0);
}).catch(console.error);
