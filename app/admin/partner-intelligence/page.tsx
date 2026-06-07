import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { ShieldAlert, CarFront, CheckCircle2 } from "lucide-react"

export default async function PartnerIntelligencePage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: partners } = await supabase
    .from('partner_trust_scores')
    .select(`
      *,
      profiles!partner_trust_scores_partner_id_fkey (
        full_name
      )
    `)
    .order('trust_score', { ascending: false })

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Partner Intelligence" 
        description="Global trust and supply reliability scoring"
      />

      <div className="grid gap-6">
        {partners?.map((partner, i) => (
          <GlassCard key={i} className="p-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div className="flex items-center gap-4">
                <div className={`p-4 rounded-full ${
                  partner.status === 'AT_RISK' ? 'bg-destructive/20 text-destructive' :
                  partner.status === 'PROBATION' ? 'bg-amber-500/20 text-amber-500' :
                  'bg-emerald-500/20 text-emerald-500'
                }`}>
                  <CarFront className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-lg">{(partner.profiles as any)?.full_name || 'Unknown Partner'}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      partner.status === 'AT_RISK' ? 'bg-destructive/20 text-destructive' :
                      partner.status === 'PROBATION' ? 'bg-amber-500/20 text-amber-500' :
                      'bg-emerald-500/20 text-emerald-500'
                    }`}>
                      {partner.status}
                    </span>
                    <span className="text-sm font-mono text-muted-foreground">ID: {partner.partner_id.split('-')[0]}</span>
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="text-3xl font-black">{partner.trust_score}</div>
                <div className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">Trust Score</div>
              </div>
            </div>

            <div className="mt-6 pt-6 border-t border-border/50 grid md:grid-cols-2 gap-6">
              <div>
                <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider mb-3">Supply Metrics</p>
                <div className="grid grid-cols-3 gap-2">
                  <div className="bg-card/50 p-2 rounded text-center">
                    <p className="text-lg font-bold">{partner.metrics.total_jobs}</p>
                    <p className="text-[10px] text-muted-foreground uppercase">Jobs</p>
                  </div>
                  <div className="bg-card/50 p-2 rounded text-center">
                    <p className="text-lg font-bold">{(partner.metrics.completion_rate * 100).toFixed(0)}%</p>
                    <p className="text-[10px] text-muted-foreground uppercase">Completion</p>
                  </div>
                  <div className="bg-card/50 p-2 rounded text-center">
                    <p className="text-lg font-bold">{partner.metrics.avg_rating.toFixed(1)}</p>
                    <p className="text-[10px] text-muted-foreground uppercase">Avg Rating</p>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider mb-3">Deterministic Factors</p>
                <ul className="space-y-1">
                  {partner.factors.map((f: string, j: number) => (
                    <li key={j} className="text-xs flex items-center gap-2">
                      {f.includes('Low') || f.includes('Elevated') || f.includes('below') ? 
                        <ShieldAlert className="w-3 h-3 text-destructive" /> :
                        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
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
