const autocannon = require('autocannon');
const { createClient } = require('@supabase/supabase-js');
const dotenv = require('dotenv');

dotenv.config({ path: '.env.local' });

async function runLoadTest() {
  console.log(`Getting admin auth token...`);
  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
  const { data: authData, error: authErr } = await supabase.auth.signInWithPassword({
    email: 'admin@onemove.demo',
    password: 'Demo@12345'
  });
  if (authErr) {
    console.error('Login Failed', authErr);
    process.exit(1);
  }
  
  const payload = encodeURIComponent(Buffer.from(JSON.stringify({
    access_token: authData.session.access_token,
    refresh_token: authData.session.refresh_token,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
    expires_in: 3600,
    token_type: 'bearer',
    user: authData.user
  })).toString('base64'));
  const cookieString = `sb-${new URL(process.env.NEXT_PUBLIC_SUPABASE_URL).hostname.split('.')[0]}-auth-token.0=${payload}`;

  console.log('Starting load test against Admin Command Center with auth cookie...');

  const instance = autocannon({
    url: 'http://localhost:3000/admin/command-center',
    connections: 10,
    pipelining: 1,
    duration: 10,
    headers: {
      cookie: cookieString
    }
  }, console.log);

  autocannon.track(instance, { renderProgressBar: true });

  instance.on('done', (result) => {
    console.log('Load test completed.');
    
    // Check our budgets
    const p95 = result.latency.p97_5; // Use 97.5 as approximation if p95 isn't output by default, or just check p99
    const p99 = result.latency.p99;
    
    console.log(`p99 latency: ${p99}ms`);
    
    if (p99 > 3000) {
      console.warn(`WARNING: p99 latency (${p99}ms) exceeded 3000ms budget.`);
    } else {
      console.log(`SUCCESS: p99 latency (${p99}ms) is within budget.`);
    }

    if (result.non2xx > 0) {
      console.error(`ERROR: ${result.non2xx} non-2xx responses detected.`);
      process.exit(1);
    } else {
      console.log('SUCCESS: 0 errors detected.');
      process.exit(0);
    }
  });
}

runLoadTest();
