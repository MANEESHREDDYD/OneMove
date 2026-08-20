'use server'

import { requireAdminApi } from '@/lib/auth/dal'

export async function POST(request: Request) {
  const guard = await requireAdminApi()
  if (!guard.ok) {
    return Response.json({ error: guard.error }, { status: guard.status })
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
