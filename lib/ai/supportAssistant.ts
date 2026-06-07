import { createClient } from '@supabase/supabase-js'
import { classifySupportTicket, SupportCategory, SupportPriority } from '../ml/supportRouting'

export async function processNewTicket(
  supabaseUrl: string, 
  supabaseServiceKey: string, 
  customerId: string, 
  description: string, 
  orderId?: string
) {
  const supabase = createClient(supabaseUrl, supabaseServiceKey)

  // 1. Run deterministic routing intelligence
  const classification = await classifySupportTicket(supabaseUrl, supabaseServiceKey, customerId, description, orderId)

  // 2. Insert into DB
  const { data, error } = await supabase
    .from('support_tickets')
    .insert([{
      customer_id: customerId,
      order_id: orderId || null,
      subject: classification.category,
      description,
      category: classification.category,
      priority: classification.priority,
      assistant_explanation: classification.assistant_explanation,
      recommended_action: classification.recommended_action,
      refund_eligibility: classification.refund_eligibility,
      escalation_required: classification.escalation_required,
      status: 'OPEN'
    }])
    .select()
    .single()

  if (error) {
    console.error('Failed to create support ticket:', error)
    throw error
  }

  return data
}
