import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { ShieldAlert, ShieldCheck, Shield } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export default async function RiskCenterPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: risks } = await supabase
    .from('risk_checks')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(10)

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Fraud Risk Center" 
        description="Deterministic Intelligence for Payment and Order Fraud"
      />

      <div className="grid gap-4">
        {risks?.map((risk, i) => (
          <GlassCard key={i} className="p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className={`p-3 rounded-full mt-1 ${
                risk.risk_level === 'CRITICAL' ? 'bg-destructive/20 text-destructive' :
                risk.risk_level === 'HIGH' ? 'bg-orange-500/20 text-orange-500' :
                'bg-emerald-500/20 text-emerald-500'
              }`}>
                {risk.risk_level === 'LOW' || risk.risk_level === 'MEDIUM' ? <ShieldCheck className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-bold font-mono text-sm uppercase">ORDER: {risk.entity_id.split('-')[0]}</h3>
                  <Badge variant={risk.risk_level === 'CRITICAL' ? 'destructive' : 'outline'}>{risk.risk_level}</Badge>
                </div>
                <ul className="space-y-1 mt-2">
                  {risk.factors.map((f: string, j: number) => (
                    <li key={j} className="text-xs text-muted-foreground flex items-center gap-2">
                      <div className="w-1 h-1 rounded-full bg-primary/50" />
                      {f}
                    </li>
                  ))}
                  {risk.factors.length === 0 && (
                    <li className="text-xs text-muted-foreground">Standard risk profile. No triggers.</li>
                  )}
                </ul>
              </div>
            </div>

            <div className="flex md:flex-col items-center gap-4 text-right bg-card/50 p-4 rounded-xl border border-border/50 min-w-[150px]">
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-bold">Action</p>
                <p className={`font-bold ${risk.action_taken === 'passed' ? 'text-emerald-500' : 'text-orange-500'}`}>
                  {risk.action_taken.toUpperCase()}
                </p>
              </div>
              <div className="text-center">
                <div className="text-2xl font-black">{risk.risk_score}</div>
                <div className="text-[10px] text-muted-foreground uppercase">Risk Score</div>
              </div>
            </div>
          </GlassCard>
        ))}

        {!risks || risks.length === 0 && (
          <div className="p-10 text-center text-muted-foreground bg-card/30 rounded-xl border border-border">
            No risk evaluations found. Run the intelligence pipeline.
          </div>
        )}
      </div>
    </div>
  )
}
