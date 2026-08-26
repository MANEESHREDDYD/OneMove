'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { simulateExperiments } from '@/lib/experiments/experimentEngine'
import { requireAdminApi } from '@/lib/auth/dal'

export async function POST(request: Request) {
  // Route Handlers are independently addressable; the page guard does not cover them.
  const guard = await requireAdminApi()
  if (!guard.ok) {
    return Response.json({ error: guard.error }, { status: guard.status })
  }

  const supabase = await createClient()
  if (!supabase) return Response.json({ error: 'Supabase setup required' }, { status: 503 })

  const formData = await request.formData()
  const action = formData.get('action') as string

  if (action === 'simulate') {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!
    await simulateExperiments(supabaseUrl, supabaseServiceKey)
  }

  revalidatePath('/admin/experiments')
  redirect('/admin/experiments')
}
