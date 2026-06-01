import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { SetupRequired } from "@/components/common/SetupRequired"
import { CheckoutClient } from './CheckoutClient'

export const dynamic = "force-dynamic";

export default async function CheckoutPage() {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Get user profile for default info
  const { data: profile } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', user.id)
    .single()

  return (
    <CheckoutClient 
      userId={user.id} 
      userName={profile?.full_name || 'Customer'}
      userPhone={profile?.phone || ''}
    />
  )
}
