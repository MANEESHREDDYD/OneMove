import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { AlertCircle, Flame, ShieldAlert, Zap } from "lucide-react"
import { Badge } from "@/components/ui/badge"

export default async function DemandIntelligencePage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: forecasts } = await supabase
    .from('demand_forecasts')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(4)

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Demand Intelligence" 
        description="Deterministic rule-based ML for predictive demand routing"
      />

      <div className="bg-primary/10 border border-primary/20 p-4 rounded-xl flex items-start gap-4">
        <AlertCircle className="w-6 h-6 text-primary mt-1" />
        <div>
          <h3 className="font-bold text-primary">Intelligence Engine Active</h3>
          <p className="text-sm text-muted-foreground mt-1">
            This module evaluates real-time location metrics and order velocity to forecast demand across 4 standard zones. 
            Confidence scores represent deterministic rule-weighting.
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {forecasts?.map((forecast, i) => (
          <GlassCard key={i} className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold flex items-center gap-2">
                {forecast.predicted_demand_level === 'SURGE' ? <Flame className="text-red-500 w-5 h-5"/> : <Zap className="text-amber-500 w-5 h-5"/>}
                {forecast.zone_id.replace('zone-', '').replace('-', ' ').toUpperCase()}
              </h2>
              <Badge variant={
                forecast.predicted_demand_level === 'SURGE' ? 'destructive' : 
                forecast.predicted_demand_level === 'HIGH' ? 'default' : 'secondary'
              }>
                {forecast.predicted_demand_level}
              </Badge>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <p className="text-sm text-muted-foreground">Expected Orders/Hr</p>
                <p className="text-2xl font-bold">{forecast.expected_order_volume}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">ML Confidence</p>
                <p className="text-2xl font-bold">{(forecast.confidence_score * 100).toFixed(0)}%</p>
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold mb-2">Deterministic Triggers:</p>
              <ul className="space-y-2">
                {forecast.factors.map((f: string, j: number) => (
                  <li key={j} className="text-xs text-muted-foreground flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          </GlassCard>
        ))}

        {!forecasts || forecasts.length === 0 && (
          <div className="col-span-full p-10 text-center text-muted-foreground bg-card/30 rounded-xl border border-border">
            No active demand forecasts. Run the intelligence pipeline.
          </div>
        )}
      </div>
    </div>
  )
}
