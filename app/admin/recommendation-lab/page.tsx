import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { Badge } from "@/components/ui/badge"

export default async function RecommendationLabPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: recommendations } = await supabase
    .from('recommendations')
    .select(`
      *,
      profiles!recommendations_customer_id_fkey (
        full_name,
        email
      )
    `)
    .order('created_at', { ascending: false })
    .limit(20)

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Recommendation Lab" 
        description="Inspect deterministic recommendation scores and traces"
      />

      <div className="bg-primary/10 border border-primary/20 p-4 rounded-xl">
        <p className="text-sm text-muted-foreground">
          This lab shows a sampled trace of the Recommendation Engine. 
          It details the deterministically calculated affinity score, confidence, and internal reasoning strings for each recommendation item attached to a customer.
        </p>
      </div>

      <div className="grid gap-6">
        {recommendations?.map((rec, i) => (
          <GlassCard key={i} className="p-6">
            <div className="flex flex-col md:flex-row justify-between md:items-center gap-4 border-b border-border/50 pb-4 mb-4">
              <div>
                <h3 className="font-bold font-mono">{(rec.profiles as { full_name?: string } | null)?.full_name || 'Customer'}</h3>
                <p className="text-xs text-muted-foreground">ID: {rec.customer_id}</p>
              </div>
              <div className="flex gap-2">
                <Badge variant="outline">{rec.entity_type}</Badge>
                <Badge className="bg-primary/20 text-primary">Score: {rec.score}</Badge>
                <Badge className="bg-emerald-500/20 text-emerald-500">Conf: {rec.confidence}</Badge>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider mb-2">Recommended Entity</p>
                <p className="font-bold truncate">{rec.entity_name || rec.entity_id}</p>
                <p className="text-xs text-muted-foreground font-mono mt-1">{rec.entity_id}</p>
              </div>
              <div>
                <p className="text-xs uppercase text-muted-foreground font-bold tracking-wider mb-2">Deterministic Reasoning</p>
                <ul className="space-y-1">
                  {rec.reasoning.map((r: string, j: number) => (
                    <li key={j} className="text-xs flex items-center gap-2">
                      <div className="w-1 h-1 bg-primary rounded-full"/> {r}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </GlassCard>
        ))}

        {!recommendations || recommendations.length === 0 && (
          <div className="text-center p-10 bg-card/50 rounded-xl border border-border">
            No recommendations generated. Run the intelligence pipeline.
          </div>
        )}
      </div>
    </div>
  )
}
