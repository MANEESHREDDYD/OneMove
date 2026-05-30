import { createBrowserClient } from '@supabase/ssr'
import { hasSupabaseConfig } from '@/utils/env'

export function createClient() {
  if (!hasSupabaseConfig()) {
    // Return a no-op client that will not crash the app.
    // Pages should check hasSupabaseConfig() and show a setup screen.
    throw new Error(
      'Supabase is not configured. Please create a .env.local file with your Supabase credentials. See docs/LOCAL_SETUP.md for instructions.'
    )
  }

  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
