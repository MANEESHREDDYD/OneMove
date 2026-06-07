'use server'

import { createClient } from '@/utils/supabase/server'
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { processNewTicket } from '@/lib/ai/supportAssistant'

export async function POST(request: Request) {
  const supabase = await createClient()
  if (!supabase) return Response.json({ error: 'Supabase setup required' })

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return Response.json({ error: 'Unauthorized' }, { status: 401 })

  const formData = await request.formData()
  const action = formData.get('action') as string

  if (action === 'create_ticket') {
    const description = formData.get('description') as string
    const orderId = formData.get('order_id') as string

    if (description) {
      const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
      const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!
      
      await processNewTicket(
        supabaseUrl, 
        supabaseServiceKey, 
        user.id, 
        description, 
        orderId || undefined
      )
    }
  }

  revalidatePath('/customer/support')
  redirect('/customer/support')
}
