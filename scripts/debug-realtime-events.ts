import { createClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';
dotenv.config({ path: '.env.local' });

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || '';
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '';
const supabase = createClient(supabaseUrl, supabaseKey);

async function checkRealtimeEvents() {
  console.log('--- Checking Realtime / Analytics Events ---');
  
  const { data: analytics, error } = await supabase
    .from('analytics_events')
    .select('*')
    .limit(10);
    
  if (error) {
    console.warn('Could not fetch analytics_events (might not exist):', error.message);
  } else {
    console.log(`✅ Found ${analytics?.length || 0} analytics events in recent history.`);
    if (analytics?.length > 0) {
      console.log('Sample Event Type:', analytics[0].event_type);
    }
  }
}

checkRealtimeEvents().catch(console.error);
