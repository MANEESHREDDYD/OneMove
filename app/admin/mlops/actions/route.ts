'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { spawn } from 'child_process'
import path from 'path'

export async function POST(request: Request) {
  const supabase = await createClient()
  if (!supabase) return Response.json({ error: 'Supabase setup required' })

  const formData = await request.formData()
  const action = formData.get('action') as string

  if (action === 'score_all') {
    // We cannot reliably await a long-running background process in a server action without timing out
    // But for demo purposes we can spawn it
    const scriptPath = path.join(process.cwd(), 'scripts', 'ml', 'score-all.ts')
    spawn('node', ['--env-file=.env.local', 'node_modules/tsx/dist/cli.mjs', scriptPath], {
      detached: true,
      stdio: 'ignore'
    }).unref()
  }

  revalidatePath('/admin/mlops')
  redirect('/admin/mlops')
}
