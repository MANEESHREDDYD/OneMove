const { Client } = require('pg');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

const client = new Client({ connectionString: process.env.DIRECT_URL });
client.connect().then(async () => {
  await client.query(`
    DROP POLICY IF EXISTS "drivers_update_orders" ON orders;
    CREATE POLICY "drivers_update_orders" ON orders FOR UPDATE 
    USING ( auth.uid() = driver_id OR driver_id IS NULL ) 
    WITH CHECK ( auth.uid() = driver_id );
  `);
  console.log("Policy updated");
  process.exit(0);
}).catch(console.error);
