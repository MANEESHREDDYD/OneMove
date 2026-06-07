import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { Store, ShieldAlert, CheckCircle2 } from "lucide-react"

export default async function MerchantIntelligencePage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: merchants } = await supabase
    .from('merchant_reliability_scores')
    .select(`
      *,
      profiles!merchant_reliability_scores_merchant_id_fkey (
        full_name
      )
    `)
    .order('reliability_score', { ascending: false })

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Merchant Intelligence" 
        description="Global reliability and SLA scoring"
      />

      <div className="grid gap-6">
        {merchants?.map((merchant, i) => (
          <GlassCard key={i} className="p-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="flex items-center gap-4">
                <div className={`p-4 rounded-full ${
                  merchant.risk_level === 'CRITICAL' ? 'bg-destructive/20 text-destructive' :
                  merchant.risk_level === 'WARNING' ? 'bg-amber-500/20 text-amber-500' :
                  'bg-emerald-500/20 text-emerald-500'
                }`}>
                  <Store className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-lg">{(merchant.profiles as any)?.full_name || 'Unknown Merchant'}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      merchant.risk_level === 'CRITICAL' ? 'bg-destructive/20 text-destructive' :
                      merchant.risk_level === 'WARNING' ? 'bg-amber-500/20 text-amber-500' :
                      'bg-emerald-500/20 text-emerald-500'
                    }`}>
                      {merchant.risk_level}
                    </span>
                    <span className="text-sm font-mono text-muted-foreground">ID: {merchant.merchant_id.split('-')[0]}</span>
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="text-3xl font-black">{merchant.reliability_score}</div>
                <div className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">Reliability Score</div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-border/50 grid md:grid-cols-2 gap-6">
              <div>
                <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider mb-3">SLA Metrics</p>
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-card/50 p-2 rounded text-center">
                    <p className="text-lg font-bold">{merchant.metrics.total_orders}</p>
                    <p className="text-[10px] text-muted-foreground uppercase">Orders</p>
                  </div>
                  <div className="bg-card/50 p-2 rounded text-center">
                    <p className="text-lg font-bold">{(merchant.metrics.cancellation_rate * 100).toFixed(0)}%</p>
                    <p className="text-[10px] text-muted-foreground uppercase">Cancels</p>
                  </div>
                  <div className="bg-card/50 p-2 rounded text-center">
                    <p className="text-lg font-bold">{merchant.metrics.avg_prep_time_mins}m</p>
                    <p className="text-[10px] text-muted-foreground uppercase">Avg Prep</p>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider mb-3">Deterministic Factors</p>
                <ul className="space-y-1">
                  {merchant.factors.map((f: string, j: number) => (
                    <li key={j} className="text-xs flex items-center gap-2">
                      {f.includes('Bonus') || f.includes('Healthy') ? 
                        <CheckCircle2 className="w-3 h-3 text-emerald-500" /> : 
                        <ShieldAlert className="w-3 h-3 text-destructive" />
                      }
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  )
}
