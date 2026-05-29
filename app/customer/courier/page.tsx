import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import { CourierFormClient } from './CourierFormClient'

export default async function CourierPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  return <CourierFormClient />
}
