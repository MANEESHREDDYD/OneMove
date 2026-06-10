import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { generateOpsInsights, OpsInsightData } from '../ml/opsAssistant'

export async function runAdminOpsAssistant(supabaseUrl: string, supabaseServiceKey: string) {
  const supabase = createClient(supabaseUrl, supabaseServiceKey)
  
  // Generate insights
  const insights = await generateOpsInsights(supabaseUrl, supabaseServiceKey)
  
  if (insights.length === 0) {
    return { count: 0, message: 'No new insights generated.' }
  }

  // Deduplicate before inserting to avoid spamming the same insights over and over
  // In a real system, we'd check against source_id.
  
  // Insert insights
  const { error } = await supabase
    .from('ops_insights')
    .insert(insights)
  
  if (error) {
    console.error('Error inserting ops insights:', error)
    throw error
  }

  return { count: insights.length, message: `Successfully generated ${insights.length} operational insights.` }
}

export async function getActiveOpsInsights(supabase: SupabaseClient) {
  const { data, error } = await supabase
    .from('ops_insights')
    .select('*')
    .eq('is_reviewed', false)
    .order('severity', { ascending: true }) // HIGH, MEDIUM, LOW - wait, alphabetical is HIGH, LOW, MEDIUM. We should order by created_at or custom logic.
    .order('created_at', { ascending: false })
  
  if (error) {
    console.error('Error fetching ops insights:', error)
    return []
  }

  // Sort: HIGH first, then MEDIUM, then LOW
  const severityOrder: Record<string, number> = { HIGH: 1, MEDIUM: 2, LOW: 3 }
  return (data ?? []).sort(
    (a: { severity: string }, b: { severity: string }) =>
      severityOrder[a.severity] - severityOrder[b.severity]
  )
}

export async function markInsightReviewed(supabase: SupabaseClient, insightId: string) {
  const { error } = await supabase
    .from('ops_insights')
    .update({ is_reviewed: true })
    .eq('id', insightId)

  if (error) {
    throw error
  }
}
