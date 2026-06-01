import { Client } from 'pg';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const directUrl = process.env.DIRECT_URL;
if (!directUrl) {
  console.error("Missing DIRECT_URL");
  process.exit(1);
}

const pgClient = new Client({ connectionString: directUrl });

async function verify() {
  await pgClient.connect();
  console.log("Verifying Demo Auth Users...\n");

  let allValid = true;

  const roles = [
    { name: 'customer', count: 50, prefix: 'customer' },
    { name: 'driver', count: 50, prefix: 'partner' },
    { name: 'merchant', count: 50, prefix: 'merchant' },
    { name: 'admin', count: 2, prefix: 'admin' },
  ];

  for (const r of roles) {
    const { rows } = await pgClient.query(`
      SELECT 
        u.id, 
        u.email, 
        p.id as profile_id, 
        p.role as profile_role
      FROM auth.users u
      LEFT JOIN profiles p ON u.id = p.id
      WHERE u.email LIKE $1
    `, [`${r.prefix}___@onemove.demo`]);

    const missing = r.count - rows.length;
    if (missing > 0) {
      console.log(`❌ Missing ${missing} generated ${r.name} users (found ${rows.length}/${r.count})`);
      allValid = false;
    } else {
      console.log(`✅ Found all ${r.count} generated ${r.name} users in auth.users`);
    }

    let profileErrors = 0;
    let roleErrors = 0;
    for (const row of rows) {
      if (!row.profile_id) profileErrors++;
      if (row.profile_role !== r.name) roleErrors++;
    }

    if (profileErrors > 0) {
      console.log(`❌ ${profileErrors} ${r.name} users missing a profile row`);
      allValid = false;
    } else {
      console.log(`✅ All ${r.name} users have exactly one matching profile row`);
    }

    if (roleErrors > 0) {
      console.log(`❌ ${roleErrors} ${r.name} profiles have incorrect role mapping`);
      allValid = false;
    } else {
      console.log(`✅ All ${r.name} profiles mapped to correct role '${r.name}'`);
    }
    
    if (r.name === 'driver') {
      const { rows: vRows } = await pgClient.query(`
        SELECT count(distinct v.driver_id) as count 
        FROM vehicles v 
        JOIN auth.users u ON v.driver_id = u.id 
        WHERE u.email LIKE 'partner___@onemove.demo'
      `);
      if (parseInt(vRows[0].count) < r.count) {
         console.log(`❌ Missing partner vehicle records. Found ${vRows[0].count}/${r.count}`);
         allValid = false;
      } else {
         console.log(`✅ All partners have matching vehicle (partner profile) records`);
      }
    }

    if (r.name === 'merchant') {
      const { rows: mRows } = await pgClient.query(`
        SELECT count(distinct m.owner_id) as count 
        FROM merchants m 
        JOIN auth.users u ON m.owner_id = u.id 
        WHERE u.email LIKE 'merchant___@onemove.demo'
      `);
      if (parseInt(mRows[0].count) < r.count) {
         console.log(`❌ Missing merchant records. Found ${mRows[0].count}/${r.count}`);
         allValid = false;
      } else {
         console.log(`✅ All merchants have matching merchant profile records`);
      }
    }
  }

  // Verify Primary accounts
  const primary = ['customer@onemove.demo', 'partner@onemove.demo', 'merchant@onemove.demo', 'admin@onemove.demo'];
  const { rows: primaryRows } = await pgClient.query(`
    SELECT u.email, p.role as profile_role 
    FROM auth.users u
    JOIN profiles p ON u.id = p.id
    WHERE u.email = ANY($1)
  `, [primary]);

  if (primaryRows.length === 4) {
    console.log(`✅ All 4 primary demo accounts exist and have profiles`);
  } else {
    console.log(`❌ Primary demo accounts missing. Found ${primaryRows.length}/4`);
    allValid = false;
  }

  console.log("\n" + "=".repeat(60));
  if (allValid) {
    console.log("🎉 VERIFICATION PASSED: All auth users, profiles, and relationships are correct.");
  } else {
    console.log("⚠️ VERIFICATION FAILED: See errors above.");
  }
  console.log("=".repeat(60) + "\n");

  await pgClient.end();
  
  if (!allValid) process.exit(1);
}

verify().catch(e => {
  console.error(e);
  process.exit(1);
});
