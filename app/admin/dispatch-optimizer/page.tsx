import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { Users, Navigation, Star, Activity } from "lucide-react"

export default async function DispatchOptimizerPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Dispatch Optimizer" 
        description="Deterministic scoring and routing intelligence"
      />

      <GlassCard className="p-6 text-center">
        <Users className="w-12 h-12 text-primary mx-auto mb-4 opacity-50" />
        <h2 className="text-xl font-bold mb-2">Real-Time Dispatch Engine</h2>
        <p className="text-muted-foreground max-w-lg mx-auto">
          The dispatch engine ranks available partners when an order is created based on distance, ratings, and reliability.
          Run the dispatch simulation script to view the live rankings.
        </p>
      </GlassCard>

      <div className="grid md:grid-cols-3 gap-6">
        <GlassCard className="p-6 bg-card/40 border-primary/20">
          <Navigation className="w-8 h-8 text-blue-500 mb-4" />
          <h3 className="font-bold mb-2">Distance Penalty</h3>
          <p className="text-sm text-muted-foreground">
            Heaviest weight. Favors partners within 2km, penalizes &gt;5km.
          </p>
        </GlassCard>
        
        <GlassCard className="p-6 bg-card/40 border-primary/20">
          <Star className="w-8 h-8 text-amber-500 mb-4" />
          <h3 className="font-bold mb-2">Rating Modifier</h3>
          <p className="text-sm text-muted-foreground">
            Boosts partners with &gt;4.9 stars, penalizes &lt;4.5 stars.
          </p>
        </GlassCard>

        <GlassCard className="p-6 bg-card/40 border-primary/20">
          <Activity className="w-8 h-8 text-emerald-500 mb-4" />
          <h3 className="font-bold mb-2">Reliability Score</h3>
          <p className="text-sm text-muted-foreground">
            Factors in historical job acceptance rate and cancellation velocity.
          </p>
        </GlassCard>
      </div>
    </div>
  )
}
