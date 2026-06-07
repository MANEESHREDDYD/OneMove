'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'
import { runAdminOpsAssistant, markInsightReviewed } from '@/lib/ai/adminOpsAssistant'
import { redirect } from 'next/navigation'

export async function POST(request: Request) {
  const supabase = await createClient()
  if (!supabase) return Response.json({ error: 'Supabase setup required' })

  const formData = await request.formData()
  const action = formData.get('action') as string

  if (action === 'generate') {
    await runAdminOpsAssistant(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!)
  } else if (action === 'mark_reviewed') {
    const insightId = formData.get('insight_id') as string
    if (insightId) {
      await markInsightReviewed(supabase, insightId)
    }
  }

  revalidatePath('/admin/ops-assistant')
  redirect('/admin/ops-assistant')
}
