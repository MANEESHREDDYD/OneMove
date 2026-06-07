import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { Users, AlertTriangle, TrendingUp, UserCheck } from "lucide-react"

export default async function CustomerSegmentsPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: segments } = await supabase
    .from('customer_segments')
    .select(`
      *,
      profiles!customer_segments_customer_id_fkey (
        full_name,
        email
      )
    `)
    .order('created_at', { ascending: false })

  // Aggregation
  const summary: Record<string, number> = {}
  segments?.forEach(s => {
    summary[s.segment_name] = (summary[s.segment_name] || 0) + 1
  })

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Customer Segmentation" 
        description="Automated cohort analysis based on purchasing patterns"
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(summary).map(([name, count], i) => (
          <GlassCard key={i} className="p-4 text-center">
            {name.includes('High-Value') ? <TrendingUp className="w-6 h-6 mx-auto mb-2 text-primary" /> :
             name.includes('Risk') ? <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-destructive" /> :
             <UserCheck className="w-6 h-6 mx-auto mb-2 text-emerald-500" />}
            <p className="text-2xl font-bold">{count}</p>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">{name}</p>
          </GlassCard>
        ))}
      </div>

      <div className="bg-card/30 border border-border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-primary/5 uppercase text-muted-foreground text-xs font-bold border-b border-border/50">
              <tr>
                <th className="px-6 py-4">Customer</th>
                <th className="px-6 py-4">Segment</th>
                <th className="px-6 py-4">Total Orders</th>
                <th className="px-6 py-4">Monthly Spend</th>
                <th className="px-6 py-4">Cancel Rate</th>
                <th className="px-6 py-4">Recency (Days)</th>
              </tr>
            </thead>
            <tbody>
              {segments?.slice(0, 50).map((s, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-card/50 transition-colors">
                  <td className="px-6 py-4 font-medium">{(s.profiles as any)?.full_name || 'Unknown'}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-[10px] font-bold ${
                      s.segment_name.includes('Risk') ? 'bg-destructive/20 text-destructive' :
                      s.segment_name.includes('High-Value') ? 'bg-primary/20 text-primary' :
                      'bg-secondary text-secondary-foreground'
                    }`}>
                      {s.segment_name}
                    </span>
                  </td>
                  <td className="px-6 py-4">{s.feature_values.order_count}</td>
                  <td className="px-6 py-4">${s.feature_values.monthly_spend.toFixed(2)}</td>
                  <td className="px-6 py-4">{(s.feature_values.cancellation_rate * 100).toFixed(1)}%</td>
                  <td className="px-6 py-4">{s.feature_values.recency_days < 0 ? '-' : s.feature_values.recency_days}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
