const { createClient } = require('@supabase/supabase-js');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

async function testAccept() {
  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  
  // Find the most recent requested ride
  const { data: orders } = await supabase.from('orders').select('id, status, driver_id').eq('status', 'requested').order('created_at', { ascending: false }).limit(1);
  if (!orders || orders.length === 0) {
    console.error("No requested orders");
    return;
  }
  
  const orderId = orders[0].id;
  console.log("Found order:", orderId);
  
  const authClient = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
  const { data: authData, error: authErr } = await authClient.auth.signInWithPassword({
    email: 'partner001@onemove.demo',
    password: 'Partner@001Move'
  });
  
  if (authErr) {
    console.error("Login failed:", authErr.message);
    return;
  }
  
  const driverId = authData.user.id;
  
  const driverClient = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, {
    global: { headers: { Authorization: `Bearer ${authData.session.access_token}` } }
  });
  
  const { data: updated, error } = await driverClient.from('orders')
    .update({ driver_id: driverId, status: 'accepted' })
    .eq('id', orderId)
    .is('driver_id', null)
    .select('id')
    .single();
    
  if (error) {
    console.error("Update failed:", error);
  } else {
    console.log("Update succeeded:", updated);
  }
}

testAccept();
