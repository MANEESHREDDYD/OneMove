import { createClient } from '@supabase/supabase-js'

export type SupportCategory = 'missing item' | 'late delivery' | 'refund request' | 'unsafe ride' | 'payment failed' | 'merchant unavailable' | 'partner no-show' | 'wrong address' | 'damaged item' | 'other'
export type SupportPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface SupportTicketClassification {
  category: SupportCategory
  priority: SupportPriority
  assistant_explanation: string
  recommended_action: string
  refund_eligibility: boolean
  escalation_required: boolean
}

export async function classifySupportTicket(
  supabaseUrl: string, 
  supabaseServiceKey: string,
  customerId: string, 
  description: string, 
  orderId?: string
): Promise<SupportTicketClassification> {
  const supabase = createClient(supabaseUrl, supabaseServiceKey)
  
  let category: SupportCategory = 'other'
  let priority: SupportPriority = 'LOW'
  let refund_eligibility = false
  let escalation_required = false
  let assistant_explanation = ''
  let recommended_action = ''

  const text = description.toLowerCase()
  let orderData = null

  if (orderId) {
    const { data } = await supabase.from('orders').select('*').eq('id', orderId).single()
    orderData = data
  }

  const { data: customerSegment } = await supabase.from('customer_segments').select('*').eq('customer_id', customerId).single()
  const { data: previousTickets } = await supabase.from('support_tickets').select('id').eq('customer_id', customerId)
  
  const ticketCount = previousTickets ? previousTickets.length : 0
  const isHighValueCustomer = customerSegment && customerSegment.segment_name === 'VIP'

  // Determine Category based on keywords
  if (text.includes('missing') && text.includes('item')) {
    category = 'missing item'
  } else if (text.includes('late') || text.includes('delay') || text.includes('where is')) {
    category = 'late delivery'
  } else if (text.includes('refund') || text.includes('money back')) {
    category = 'refund request'
  } else if (text.includes('unsafe') || text.includes('accident') || text.includes('danger')) {
    category = 'unsafe ride'
  } else if (text.includes('payment') || text.includes('charge')) {
    category = 'payment failed'
  } else if (text.includes('damaged') || text.includes('broken') || text.includes('spilled')) {
    category = 'damaged item'
  } else if (text.includes('wrong address')) {
    category = 'wrong address'
  } else if (text.includes('partner') && (text.includes('no show') || text.includes('did not arrive'))) {
    category = 'partner no-show'
  }

  let riskScore = 0
  if (orderId) {
    const { data: riskData } = await supabase.from('risk_checks').select('risk_score').eq('order_id', orderId).single()
    if (riskData) riskScore = riskData.risk_score
  }

  // Determine Priority
  if (category === 'unsafe ride') {
    priority = 'CRITICAL'
    escalation_required = true
    assistant_explanation = 'Safety-related keywords detected.'
    recommended_action = 'Immediately escalate to Trust & Safety team.'
  } else if (ticketCount > 3 && isHighValueCustomer) {
    priority = 'HIGH'
    assistant_explanation = 'VIP customer with multiple recent tickets.'
    recommended_action = 'Provide white-glove support and apologies.'
  } else if (riskScore > 70) {
    priority = 'HIGH'
    assistant_explanation = 'Associated order has high fraud risk score.'
    recommended_action = 'Review account for potential policy violation.'
    escalation_required = true
  } else if (orderData && orderData.total_amount > 100) {
    priority = 'MEDIUM'
    assistant_explanation = 'High-value order (>$100).'
    recommended_action = 'Review details before issuing a refund.'
  } else {
    assistant_explanation = 'Standard ticket processing.'
    recommended_action = 'Follow standard operating procedure.'
  }

  // Determine Refund Eligibility
  if (orderData && ['missing item', 'damaged item', 'late delivery'].includes(category)) {
    if (riskScore < 50 && ticketCount < 5) {
      refund_eligibility = true
      assistant_explanation += ' Customer is eligible for an automated refund based on low risk score and valid complaint category.'
      recommended_action = 'Offer partial or full refund to wallet.'
    } else {
      assistant_explanation += ' Not eligible for automated refund due to high risk or ticket frequency.'
      recommended_action = 'Investigate claim manually.'
    }
  }

  return {
    category,
    priority,
    assistant_explanation,
    recommended_action,
    refund_eligibility,
    escalation_required
  }
}
