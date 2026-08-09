/* eslint-disable @typescript-eslint/no-require-imports */
const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = process.env.SUPABASE_URL || 'http://127.0.0.1:54321';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

const supabaseAnon = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
const supabaseAdmin = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

async function runTests() {
  console.log('--- STARTING FR-2 SECURITY TESTS ---');
  let passed = 0;
  let failed = 0;

  function assertCondition(condition, message) {
    if (condition) {
      console.log(`[PASS] ${message}`);
      passed++;
    } else {
      console.log(`[FAIL] ${message}`);
      failed++;
    }
  }

  try {
    // 1. Signup with crafted metadata to mint admin
    console.log('\\n1. Testing role minting via signup...');
    const email = `test_hacker_${Date.now()}@example.com`;
    const password = 'Password123!';
    const { data: signUpData, error: signUpError } = await supabaseAnon.auth.signUp({
      email,
      password,
      options: {
        data: {
          role: 'admin', // Attempt to inject admin role
          name: 'Hacker User'
        }
      }
    });
    
    if (signUpError) throw signUpError;
    const userId = signUpData.user.id;

    // Check actual role in profiles
    const { data: profile, error: profileError } = await supabaseAnon
      .from('profiles')
      .select('role')
      .eq('id', userId)
      .single();
    
    console.log('Profile:', profile); console.log('ProfileErr:', profileError); assertCondition(!profileError && profile && profile.role === 'customer', 'User created with customer role despite admin metadata injection');

    // 2. Cross-tenant profile reads fail
    console.log('\\n2. Testing cross-tenant profile reads...');
    const email2 = `test_hacker2_${Date.now()}@example.com`;
    await supabaseAnon.auth.signUp({ email: email2, password });
    
    // Log in as user 1
    const { data: loginData } = await supabaseAnon.auth.signInWithPassword({ email, password });
    const user1Client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      global: { headers: { Authorization: `Bearer ${loginData.session.access_token}` } }
    });

    // Attempt to read all profiles
    const { data: allProfiles } = await user1Client.from('profiles').select('*');
    console.log('All Profiles:', allProfiles); assertCondition(allProfiles && allProfiles.length === 1, 'Ordinary user can only read their own profile');

    // 3. User cannot modify privileged profile roles
    console.log('\\n3. Testing privilege escalation via UPDATE...');
    const { error: updateError } = await user1Client
      .from('profiles')
      .update({ role: 'admin' })
      .eq('id', userId);
    
    assertCondition(updateError !== null, 'Ordinary user blocked from updating own role to admin');

    // 4. Tracking is not globally readable
    console.log('\\n4. Testing tracking visibility...');
    const { data: trackingData } = await user1Client.from('tracking').select('*');
    console.log('Tracking Data:', trackingData); assertCondition(trackingData && trackingData.length === 0, 'Tracking data is not globally readable by default customer');

    // 5. Arbitrary financial mutations fail
    console.log('\\n5. Testing financial mutations...');
    // Create an order via admin for user 1
    const { data: newOrder } = await supabaseAdmin.from('orders').insert({
      customer_id: userId,
      service_type: 'ride',
      total_amount: 15.00,
      pickup_location: {lat: 0, lng: 0, address: "A"},
      dropoff_location: {lat: 1, lng: 1, address: "B"}
    }).select().single();

    if (newOrder) {
      // User 1 tries to change the price
      const { error: orderUpdateError } = await user1Client
        .from('orders')
        .update({ total_amount: 0.00 })
        .eq('id', newOrder.id);
      
      assertCondition(orderUpdateError !== null, 'User blocked from altering order total_amount');
    } else {
      console.log('[WARN] Could not create test order');
    }

  } catch (err) {
    console.error('Test execution error:', err);
  }

  console.log(`\\n--- RESULTS: ${passed} Passed, ${failed} Failed ---`);
}

runTests();


