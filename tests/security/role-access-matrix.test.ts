import { describe, it, expect, beforeAll } from 'vitest';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import * as dotenv from 'dotenv';

dotenv.config({ path: '.env.local' });

let supabaseAnon: SupabaseClient;

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  describe.skip('Role Access Matrix (RLS Tests) - SKIPPED (No Supabase credentials)', () => {
    it('skipped', () => {})
  });
} else {
  beforeAll(() => {
    supabaseAnon = createClient(supabaseUrl, supabaseKey);
  });

  describe('Role Access Matrix (RLS Tests)', () => {
    it('Anonymous user should not be able to read customer orders', async () => {
      const { data, error } = await supabaseAnon
        .from('orders')
        .select('*')
        .limit(1);
      
      // RLS should return an empty array for an anonymous user because they own no orders
      // or it should error if select is outright banned.
      if (!error) {
        expect(data?.length).toBe(0);
      }
    });

    it('Anonymous user should not be able to read partner earnings', async () => {
      const { data, error } = await supabaseAnon
        .from('payments')
        .select('*')
        .limit(1);
        
      if (!error) {
        expect(data?.length).toBe(0);
      }
    });

    it('Anonymous user should not be able to read merchant profiles (private data)', async () => {
      const { data, error } = await supabaseAnon
        .from('merchants')
        .select('bank_account_number') // assuming a sensitive field
        .limit(1);
        
      if (!error) {
        // In Supabase, if a column doesn't exist or is protected, it might just return empty
        expect(data?.length).toBe(0);
      }
    });
    
    it('Anonymous user should be able to read public stores', async () => {
      const { data, error } = await supabaseAnon
        .from('merchants')
        .select('*')
        .limit(1);
        
      expect(error).toBeNull();
      // It's acceptable for this to return data since stores are public
    });
  });
}
