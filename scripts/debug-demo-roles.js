const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

const envPath = path.join(process.cwd(), '.env.local');
const envVars = {};

if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.substring(0, eqIdx).trim();
    let value = trimmed.substring(eqIdx + 1).trim();
    if (value.startsWith('"') && value.endsWith('"')) value = value.substring(1, value.length - 1);
    envVars[key] = value;
  }
}

const directUrl = envVars['DIRECT_URL'];
if (!directUrl) { console.error("Missing DIRECT_URL in .env.local"); process.exit(1); }

const DEMO_EMAILS = [
  { email: 'customer@onemove.demo', expectedRole: 'customer', expectedRoute: '/customer' },
  { email: 'partner@onemove.demo', expectedRole: 'driver', expectedRoute: '/partner' },
  { email: 'merchant@onemove.demo', expectedRole: 'merchant', expectedRoute: '/merchant' },
  { email: 'admin@onemove.demo', expectedRole: 'admin', expectedRoute: '/admin/command-center' },
];

async function run() {
  const client = new Client({ connectionString: directUrl });
  await client.connect();
  console.log("✅ Connected to database.\n");

  console.log("=".repeat(80));
  console.log("DEMO ROLE DEBUG REPORT");
  console.log("=".repeat(80));

  let allGood = true;

  for (const demo of DEMO_EMAILS) {
    const { rows: authRows } = await client.query(
      `SELECT id, email, raw_user_meta_data->>'role' as meta_role FROM auth.users WHERE email = $1`,
      [demo.email]
    );

    if (authRows.length === 0) {
      console.log(`\n❌ ${demo.email}`);
      console.log(`   auth_user_id: NOT FOUND`);
      console.log(`   status: MISSING - User not in auth.users. Run: npm run seed:auth`);
      allGood = false;
      continue;
    }

    const authUser = authRows[0];
    const { rows: profileRows } = await client.query(
      `SELECT id, role, full_name FROM profiles WHERE id = $1`,
      [authUser.id]
    );

    const profile = profileRows[0];
    const actualRole = profile?.role || 'NO PROFILE';
    const roleMatch = actualRole === demo.expectedRole;
    const routePrefix = actualRole === 'driver' ? 'partner' : actualRole;
    const actualRoute = actualRole === 'admin' ? '/admin/command-center' : `/${routePrefix}`;

    console.log(`\n${roleMatch ? '✅' : '❌'} ${demo.email}`);
    console.log(`   auth_user_id:     ${authUser.id}`);
    console.log(`   meta_role:        ${authUser.meta_role || 'null'}`);
    console.log(`   profile_id:       ${profile?.id || 'MISSING'}`);
    console.log(`   profile_role:     ${actualRole}`);
    console.log(`   expected_role:    ${demo.expectedRole}`);
    console.log(`   expected_route:   ${demo.expectedRoute}`);
    console.log(`   actual_route:     ${actualRoute}`);
    console.log(`   status:           ${roleMatch ? 'OK' : 'ROLE MISMATCH'}`);

    if (!roleMatch) {
      allGood = false;
      // Auto-fix: update profile role
      if (profile) {
        console.log(`   🔧 Auto-fixing: updating profile role to '${demo.expectedRole}'...`);
        await client.query(`UPDATE profiles SET role = $1 WHERE id = $2`, [demo.expectedRole, authUser.id]);
        console.log(`   ✅ Fixed.`);
      }
    }
  }

  console.log("\n" + "=".repeat(80));
  console.log(allGood ? "✅ ALL DEMO ROLES CORRECT" : "⚠️  SOME ROLES WERE MISMATCHED (auto-fixed above)");
  console.log("=".repeat(80));

  await client.end();
}

run().catch(err => { console.error(err); process.exit(1); });
