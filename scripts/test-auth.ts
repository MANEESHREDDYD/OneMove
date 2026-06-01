import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
import * as path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !anonKey) {
  console.error("Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY");
  process.exit(1);
}

const supabase = createClient(supabaseUrl, anonKey, {
  auth: {
    persistSession: false,
    autoRefreshToken: false,
  }
});

async function runTest() {
  console.log("Running Auth Sign-out Flow Test...\n");
  
  const testEmail = 'customer@onemove.demo';
  const testPassword = 'Demo@12345';

  console.log(`1. Signing in as ${testEmail}...`);
  const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
    email: testEmail,
    password: testPassword,
  });

  if (signInError) {
    console.error("❌ Sign in failed:", signInError.message);
    process.exit(1);
  }
  console.log("✅ Signed in successfully.");
  console.log("Session Access Token exists:", !!signInData.session?.access_token);

  console.log("\n2. Calling Sign Out...");
  const { error: signOutError } = await supabase.auth.signOut();
  if (signOutError) {
    console.error("❌ Sign out failed:", signOutError.message);
    process.exit(1);
  }
  
  console.log("✅ Sign out called successfully.");
  
  console.log("\n3. Verifying session is destroyed...");
  const { data: sessionData } = await supabase.auth.getSession();
  
  if (sessionData.session) {
    console.error("❌ Session still exists after sign out!");
    process.exit(1);
  } else {
    console.log("✅ Session successfully cleared.");
  }

  console.log("\n🎉 Auth test passed. (Note: Client-side cookies and redirects must also be tested manually).");
}

runTest().catch(console.error);
