import { createClient } from '@supabase/supabase-js';
import { Client } from 'pg';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const directUrl = process.env.DIRECT_URL;

if (!supabaseUrl || !serviceRoleKey || !directUrl) {
  console.error("Missing NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or DIRECT_URL");
  process.exit(1);
}

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: { autoRefreshToken: false, persistSession: false }
});

const PRIMARY_DEMO = [
  { email: 'customer@onemove.demo', password: 'Demo@12345', name: 'Demo Customer', role: 'customer' },
  { email: 'partner@onemove.demo', password: 'Demo@12345', name: 'Demo Partner', role: 'driver' },
  { email: 'merchant@onemove.demo', password: 'Demo@12345', name: 'Demo Merchant', role: 'merchant' },
  { email: 'admin@onemove.demo', password: 'Demo@12345', name: 'Demo Admin', role: 'admin' }
];

async function generateUsers(prefix: string, role: string, count: number) {
  const users = [];
  for (let i = 1; i <= count; i++) {
    const num = String(i).padStart(3, '0');
    users.push({
      email: `${prefix}${num}@onemove.demo`,
      password: `${prefix.charAt(0).toUpperCase() + prefix.slice(1)}@${num}Move`,
      name: `Demo ${prefix.charAt(0).toUpperCase() + prefix.slice(1)} ${num}`,
      role: role
    });
  }
  return users;
}

async function seed() {
  console.log("Seeding Auth Users...");

  const allUsers = [
    ...PRIMARY_DEMO,
    ...(await generateUsers('customer', 'customer', 50)),
    ...(await generateUsers('partner', 'driver', 50)),
    ...(await generateUsers('merchant', 'merchant', 50)),
    ...(await generateUsers('admin', 'admin', 2))
  ];

  // We use pg to check existence quickly and avoid API rate limits for reading
  const pgClient = new Client({ connectionString: directUrl });
  await pgClient.connect();

  let successCount = 0;
  
  for (const u of allUsers) {
    let authUserId: string;

    const { rows } = await pgClient.query("SELECT id FROM auth.users WHERE email = $1", [u.email]);
    
    if (rows.length > 0) {
      authUserId = rows[0].id;
      // Update password & metadata via admin api
      const { error: updateError } = await supabase.auth.admin.updateUserById(authUserId, {
        password: u.password,
        user_metadata: { name: u.name, role: u.role }
      });
      if (updateError) {
        console.error(`Failed to update ${u.email}:`, updateError.message);
      }
    } else {
      // Create new
      const { data: createData, error: createError } = await supabase.auth.admin.createUser({
        email: u.email,
        password: u.password,
        email_confirm: true,
        user_metadata: { name: u.name, role: u.role }
      });
      if (createError) {
        console.error(`Failed to create ${u.email}:`, createError.message);
        continue;
      }
      authUserId = createData.user.id;
    }

    // Ensure profile has correct role
    await pgClient.query(
      `INSERT INTO profiles (id, full_name, role, is_demo) 
       VALUES ($1, $2, $3, true)
       ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role, full_name = EXCLUDED.full_name, is_demo = true`,
      [authUserId, u.name, u.role]
    );

    // If merchant, ensure merchant row exists
    if (u.role === 'merchant') {
      const { rows: merchantRows } = await pgClient.query("SELECT id FROM merchants WHERE owner_id = $1", [authUserId]);
      if (merchantRows.length === 0) {
        await pgClient.query(
          `INSERT INTO merchants (id, owner_id, name, category, status, address_line1, latitude, longitude, is_demo)
           VALUES (gen_random_uuid(), $1, $2, 'grocery', 'active', '123 Demo St', 40.7128, -74.0060, true)`,
          [authUserId, `${u.name} Store`]
        );
      }
    }

    // If partner/driver, ensure vehicle row exists
    if (u.role === 'driver') {
      const { rows: vehicleRows } = await pgClient.query("SELECT id FROM vehicles WHERE driver_id = $1", [authUserId]);
      if (vehicleRows.length === 0) {
        await pgClient.query(
          `INSERT INTO vehicles (id, driver_id, make, model, plate_number, color, type, is_demo)
           VALUES (gen_random_uuid(), $1, 'Toyota', 'Camry', $2, 'Silver', 'car', true)`,
          [authUserId, 'DEMO' + String(Math.floor(Math.random() * 9000) + 1000)]
        );
      }
    }

    successCount++;
    if (successCount % 20 === 0) {
      console.log(`Processed ${successCount}/${allUsers.length} users...`);
    }
  }

  await pgClient.end();
  console.log(`\nSuccessfully created/updated ${successCount} demo users.`);
  console.log("Done.");
}

seed().catch(err => {
  console.error(err);
  process.exit(1);
});
