import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import { Star, MapPin, Sparkles } from "lucide-react"

export default async function CustomerRecommendationsPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />
  
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/auth/login')

  const { data: recommendations } = await supabase
    .from('recommendations')
    .select('*')
    .eq('customer_id', user.id)
    .order('score', { ascending: false })

  const merchants = recommendations?.filter(r => r.entity_type === 'merchant') || []
  const rides = recommendations?.filter(r => r.entity_type === 'ride_destination') || []

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="For You" 
        description="Smart recommendations powered by deterministic intelligence"
      />

      <section>
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <Star className="text-amber-500 w-5 h-5" /> Recommended Merchants
        </h2>
        {merchants.length === 0 ? (
          <p className="text-muted-foreground text-sm">Make some orders to get personalized merchant recommendations.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {merchants.map((rec) => (
              <GlassCard key={rec.id} className="p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold">{rec.entity_name}</h3>
                  <div className="bg-primary/10 text-primary px-2 py-1 rounded-full text-xs font-bold">
                    {rec.score} Score
                  </div>
                </div>
                <div className="mt-4">
                  <p className="text-xs text-muted-foreground font-semibold mb-1 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-emerald-500" /> Why we suggest this:
                  </p>
                  <ul className="space-y-1">
                    {rec.reasoning.map((reason: string, i: number) => (
                      <li key={i} className="text-xs text-muted-foreground ml-4 list-disc">{reason}</li>
                    ))}
                  </ul>
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
          <MapPin className="text-blue-500 w-5 h-5" /> Suggested Destinations
        </h2>
        {rides.length === 0 ? (
          <p className="text-muted-foreground text-sm">Take some rides to get personalized destination suggestions.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {rides.map((rec) => (
              <GlassCard key={rec.id} className="p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold truncate max-w-[200px]">{rec.entity_name}</h3>
                  <div className="bg-primary/10 text-primary px-2 py-1 rounded-full text-xs font-bold">
                    {rec.score} Score
                  </div>
                </div>
                <div className="mt-4">
                  <p className="text-xs text-muted-foreground font-semibold mb-1 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-emerald-500" /> Why we suggest this:
                  </p>
                  <ul className="space-y-1">
                    {rec.reasoning.map((reason: string, i: number) => (
                      <li key={i} className="text-xs text-muted-foreground ml-4 list-disc">{reason}</li>
                    ))}
                  </ul>
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
