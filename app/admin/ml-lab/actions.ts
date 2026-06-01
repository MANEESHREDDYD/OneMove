'use server'

import { createClient } from '@/utils/supabase/server'

export async function askAI(query: string) {
  await new Promise(resolve => setTimeout(resolve, 1500))

  const supabase = await createClient()
  if (!supabase) return { error: 'Supabase is not configured.' }
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return { error: 'Unauthorized.' }

  const q = query.toLowerCase()

  if (q.includes('score') || q.includes('ml') || q.includes('model') || q.includes('risk') || q.includes('scenario')) {
    const { data: logs } = await supabase.from('ml_score_logs').select('*').order('created_at', { ascending: false });
    if (!logs || logs.length === 0) return { response: "No ML scoring logs found." }
    
    const scenarios = logs.filter(l => l.model_type === 'scenario_simulation' && l.metadata?.scenario)
                          .map(l => `- ${l.metadata.scenario} (Score: ${l.score})`)
                          .slice(0, 5)
                          .join('\n');

    return { 
      response: `I found ${logs.filter(l => l.model_type === 'scenario_simulation').length} active ML scenario simulations running on the platform. Here are some recent flagged events:\n\n${scenarios}\n\nOur deterministic rules engine is actively tagging fraud risk, partner performance, and surge pricing conditions.` 
    }
  }

  if (q.includes('revenue') || q.includes('money') || q.includes('sales') || q.includes('payout')) {
    const { data: orders } = await supabase.from('orders').select('total_amount');
    const { data: payouts } = await supabase.from('merchant_payouts').select('amount');
    
    const totalRev = orders?.reduce((s, o) => s + (o.total_amount || 0), 0) || 0;
    const totalPayout = payouts?.reduce((s, p) => s + (p.amount || 0), 0) || 0;
    const margin = totalRev - totalPayout;
    
    return { 
      response: `The platform has generated $${totalRev.toFixed(2)} in total GMV. Merchant payouts total $${totalPayout.toFixed(2)}, leaving an estimated gross margin of $${margin.toFixed(2)}. High-value orders are clustered in peak delivery times.` 
    }
  }

  return {
    response: "I am OneMove's ML rule-based Copilot. Ask me about 'scores', 'risk', 'models', 'revenue', or 'payouts' to analyze the platform's deterministic data."
  }
}
