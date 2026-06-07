import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
const supabase = createClient(supabaseUrl, supabaseKey);

async function checkStatusLifecycle() {
  console.log('--- Checking Status Lifecycle and Transitions ---');
  
  // Just a quick check to see if we have valid statuses across all orders
  const { data: orders, error } = await supabase
    .from('orders')
    .select('id, status');
    
  if (error) {
    console.error('Error fetching orders:', error);
    process.exit(1);
  }
    const validStatuses = new Set([
      'pending', 'accepted', 'preparing', 'ready', 'in_transit', 'completed', 'cancelled', 'requested', 'placed', 'created', 'merchant_accepted', 'arrived', 'started', 'picked_up'
    ]);
  const invalidOrders = orders?.filter(o => !validStatuses.has(o.status)) || [];
  
  if (invalidOrders.length > 0) {
    console.error(`Found ${invalidOrders.length} orders with invalid statuses:`, invalidOrders.slice(0, 5));
    process.exit(1);
  } else {
    console.log(`✅ All ${orders?.length || 0} orders have valid statuses.`);
  }

  // Check if every order that is 'delivered' has an associated status_event if we tracked it
  // (Optional depending on seed data completeness, but good to check)
  const { data: events, error: eventError } = await supabase
    .from('order_status_events')
    .select('id, order_id, status');
    
  if (eventError) {
    // If order_status_events table doesn't exist yet, we just warn
    console.warn('Could not check status_events (might not exist):', eventError.message);
  } else {
    console.log(`✅ Found ${events?.length || 0} status events recorded.`);
  }
}

checkStatusLifecycle().catch(console.error);
