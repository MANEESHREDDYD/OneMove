import { createClient } from '@supabase/supabase-js'
import { getDeterministicAssignment } from './assignment'

export async function simulateExperiments(supabaseUrl: string, supabaseServiceKey: string) {
  const supabase = createClient(supabaseUrl, supabaseServiceKey)

  // 1. Fetch active experiments & variants
  const { data: experiments } = await supabase.from('experiments').select('id, status').eq('status', 'ACTIVE')
  if (!experiments || experiments.length === 0) return

  // 2. Fetch customers (take a sample of 100 for simulation)
  const { data: customers } = await supabase.from('profiles').select('id').eq('role', 'customer').limit(100)
  if (!customers) return

  // For each experiment, assign customers and simulate events
  for (const exp of experiments) {
    const { data: variants } = await supabase.from('experiment_variants').select('id').eq('experiment_id', exp.id)
    if (!variants || variants.length === 0) continue

    let variantAssignments = variants.map(v => ({ id: v.id, count: 0, conversions: 0, revenue: 0 }))

    for (const customer of customers) {
      // Assignment
      const variantIdx = getDeterministicAssignment(customer.id, exp.id, variants.length)
      const assignedVariantId = variants[variantIdx].id

      // Record Assignment
      const { data: assignmentData } = await supabase.from('experiment_assignments').insert([{
        experiment_id: exp.id,
        variant_id: assignedVariantId,
        customer_id: customer.id,
        session_id: `sim-${Date.now()}`
      }]).select('id').single()

      if (!assignmentData) continue
      
      variantAssignments[variantIdx].count += 1

      // Simulate Impression Event
      await supabase.from('experiment_events').insert([{
        assignment_id: assignmentData.id,
        event_type: 'impression',
        value: 0
      }])

      // Simulate Conversion Event (Randomized based on deterministic hash but biased to variant index for demo)
      // e.g. variant 1 has slightly higher conversion than variant 0
      const rand = getDeterministicAssignment(`${customer.id}-conv`, exp.id, 100)
      const conversionThreshold = 20 + (variantIdx * 10) // Variant 0: 20%, Variant 1: 30%, etc.
      
      if (rand < conversionThreshold) {
        const orderValue = 15 + getDeterministicAssignment(`${customer.id}-value`, exp.id, 50)
        await supabase.from('experiment_events').insert([{
          assignment_id: assignmentData.id,
          event_type: 'conversion',
          value: orderValue
        }])
        
        variantAssignments[variantIdx].conversions += 1
        variantAssignments[variantIdx].revenue += orderValue
      }
    }

    // 3. Update Metrics Table
    for (const va of variantAssignments) {
      const cr = va.count > 0 ? (va.conversions / va.count) * 100 : 0
      const aov = va.conversions > 0 ? (va.revenue / va.conversions) : 0
      
      let recommendation = 'needs more data'
      if (va.count > 30) {
        if (cr > 25) recommendation = 'continue (winning)'
        else if (cr < 15) recommendation = 'stop (underperforming)'
      }

      await supabase.from('experiment_metrics').upsert({
        experiment_id: exp.id,
        variant_id: va.id,
        impressions: va.count,
        conversions: va.conversions,
        conversion_rate: cr,
        aov: aov,
        revenue: va.revenue,
        sample_size: va.count,
        recommendation: recommendation,
        created_at: new Date().toISOString()
      }, { onConflict: 'experiment_id, variant_id' }) // requires unique constraint
    }
  }
}
