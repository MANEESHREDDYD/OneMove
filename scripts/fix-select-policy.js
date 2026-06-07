const { Client } = require('pg');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

const client = new Client({ connectionString: process.env.DIRECT_URL });
client.connect().then(async () => {
  await client.query(`
    DROP POLICY IF EXISTS "partners_select_jobs" ON orders;
    CREATE POLICY "partners_select_jobs" ON orders FOR SELECT 
    USING ( status IN ('pending', 'placed', 'merchant_accepted', 'preparing', 'ready', 'requested', 'accepted', 'in_transit', 'completed', 'delivered') OR driver_id = auth.uid() );
  `);
  console.log("Select Policy updated");
  process.exit(0);
}).catch(console.error);
