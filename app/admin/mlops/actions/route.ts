'use server'

import { createClient } from '@/utils/supabase/server'

export async function POST(request: Request) {
  const supabase = await createClient()
  if (!supabase) {
    return Response.json({ error: 'Supabase setup required' }, { status: 503 })
  }

  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single()
  if (profile?.role !== 'admin') {
    return Response.json({ error: 'Forbidden' }, { status: 403 })
  }

  const formData = await request.formData()
  const action = formData.get('action')

  if (action === 'score_all') {
    return Response.json(
      {
        error: 'Durable private executor is not configured',
        code: 'DURABLE_EXECUTOR_REQUIRED',
      },
      {
        status: 503,
        headers: { 'Cache-Control': 'no-store' },
      },
    )
  }

  return Response.json({ error: 'Unsupported action' }, { status: 400 })
}
