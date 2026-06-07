import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { TrendingUp, AlertCircle, Clock, ShieldCheck, ShieldAlert } from "lucide-react"

export default async function MerchantInsightsPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: scoreData } = await supabase
    .from('merchant_reliability_scores')
    .select('*')
    .eq('merchant_id', user.id)
    .single()

  if (!scoreData) {
    return (
      <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <PageHeader title="Platform Insights" description="Your performance and intelligence data" />
        <div className="text-center p-10 bg-card/50 rounded-xl border border-border">
          Intelligence data is currently being generated. Please check back later.
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Platform Insights" 
        description="Your performance and intelligence data"
      />

      <div className="grid md:grid-cols-3 gap-6">
        <GlassCard className="p-6 md:col-span-2 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-6 opacity-10">
            {scoreData.reliability_score > 80 ? <ShieldCheck className="w-32 h-32" /> : <ShieldAlert className="w-32 h-32" />}
          </div>
          <h2 className="text-xl font-bold mb-2">Platform Reliability Score</h2>
          <p className="text-sm text-muted-foreground mb-6 max-w-md">
            This score determines your visibility in customer recommendations and search ranking algorithms.
          </p>
          <div className="flex items-end gap-4">
            <div className="text-6xl font-black">{scoreData.reliability_score}</div>
            <div className={`px-3 py-1 rounded-full text-sm font-bold mb-2 ${
              scoreData.risk_level === 'CRITICAL' ? 'bg-destructive/20 text-destructive' :
              scoreData.risk_level === 'WARNING' ? 'bg-amber-500/20 text-amber-500' :
              'bg-emerald-500/20 text-emerald-500'
            }`}>
              {scoreData.risk_level}
            </div>
          </div>
        </GlassCard>

        <GlassCard className="p-6">
          <h3 className="font-bold mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-500" /> SLA Metrics
          </h3>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-muted-foreground">Cancellation Rate</span>
                <span className="font-bold">{(scoreData.metrics.cancellation_rate * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                <div className={`h-full ${scoreData.metrics.cancellation_rate > 0.05 ? 'bg-destructive' : 'bg-emerald-500'}`} style={{ width: `${Math.min(100, scoreData.metrics.cancellation_rate * 100)}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-muted-foreground">Avg Prep Time</span>
                <span className="font-bold">{scoreData.metrics.avg_prep_time_mins} min</span>
              </div>
              <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                <div className={`h-full ${scoreData.metrics.avg_prep_time_mins > 25 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(100, (scoreData.metrics.avg_prep_time_mins / 45) * 100)}%` }} />
              </div>
            </div>
          </div>
        </GlassCard>
      </div>

      <GlassCard className="p-6">
        <h3 className="font-bold mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-primary" /> Algorithmic Feedback
        </h3>
        <ul className="grid md:grid-cols-2 gap-4">
          {scoreData.factors.map((f: string, i: number) => (
            <li key={i} className="flex items-start gap-3 bg-card/50 p-4 rounded-lg border border-border/50">
              <AlertCircle className="w-5 h-5 text-primary shrink-0 mt-0.5" />
              <span className="text-sm">{f}</span>
            </li>
          ))}
        </ul>
      </GlassCard>
    </div>
  )
}
