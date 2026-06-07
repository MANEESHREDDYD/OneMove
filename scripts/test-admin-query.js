const { createClient } = require('@supabase/supabase-js');
const dotenv = require('dotenv');
dotenv.config({ path: '.env.local' });

(async () => {
  const supabaseAdmin = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY);
  
  // 1. Get the latest completed order ID
  const { data: orderRow } = await supabaseAdmin.from('orders').select('id').order('created_at', { ascending: false }).limit(1).single();
  const rideId = orderRow.id;
  console.log('Testing with Order ID:', rideId);

  // 2. Simulate Admin login
  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
  const { data: authData, error: authErr } = await supabase.auth.signInWithPassword({
    email: 'admin@onemove.demo',
    password: 'Demo@12345'
  });
  if (authErr) {
    console.error('Login Failed', authErr);
    process.exit(1);
  }
  console.log('Logged in as admin. UID:', authData.user.id);

  // 3. Run the exact query from the Admin page
  const { data: order, error } = await supabase
    .from('orders')
    .select(`
      *,
      order_items (
        id, quantity, unit_price,
        products ( name )
      ),
      payments ( amount, method, status )
    `)
    .eq('id', rideId)
    .single();

  if (error) {
    console.error('QUERY ERROR:', error);
  }
  if (!order) {
    console.error('NO ORDER RETURNED!');
  } else {
    console.log('Order found successfully!', order.id, order.status);
  }
  
})();
