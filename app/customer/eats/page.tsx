import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import Link from "next/link"
import { Star, Clock, Flame } from "lucide-react"
import { createClient } from "@/utils/supabase/server"
import { SetupRequired } from "@/components/common/SetupRequired"

export const dynamic = "force-dynamic";

export default async function EatsMarketplace() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  const { data: merchants, error } = await supabase
    .from('merchants')
    .select('*')
    .eq('category', 'restaurant')
    .order('rating', { ascending: false })

  if (error) {
    console.error('Error fetching merchants:', error)
  }

  const featuredMerchants = merchants?.slice(0, 4) || []
  const allMerchants = merchants || []

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="OneMove Eats" 
        description="Craving something? We'll bring it."
      />

      {/* Featured Section */}
      {featuredMerchants.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold tracking-tight flex items-center gap-2">
            <Flame className="h-5 w-5 text-orange-500" />
            Trending Near You
          </h2>
          <div className="flex gap-4 overflow-x-auto pb-4 snap-x hide-scrollbar">
            {featuredMerchants.map(restaurant => (
              <Link key={restaurant.id} href={`/customer/eats/${restaurant.id}`} className="snap-start shrink-0 w-[280px]">
                <GlassCard className="overflow-hidden hover:ring-2 hover:ring-primary/50 transition-all cursor-pointer">
                  <div className="h-32 bg-primary/20 w-full flex items-center justify-center">
                     <p className="text-muted-foreground font-medium">{restaurant.category} Cuisine</p>
                  </div>
                  <div className="p-4">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-bold truncate pr-2">{restaurant.name}</h3>
                      <div className="flex items-center gap-1 bg-background/80 px-1.5 py-0.5 rounded-md text-xs font-bold">
                        <Star className="h-3 w-3 text-yellow-500 fill-yellow-500" />
                        {restaurant.rating}
                      </div>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground font-medium">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        25-40 min
                      </span>
                    </div>
                  </div>
                </GlassCard>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* All Restaurants */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">All Restaurants</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {allMerchants.map(restaurant => (
            <Link key={restaurant.id} href={`/customer/eats/${restaurant.id}`}>
              <GlassCard className="p-3 flex items-center gap-4 hover:bg-white/5 transition-colors cursor-pointer group">
                <div className="h-16 w-16 bg-primary/10 rounded-lg flex items-center justify-center shrink-0 overflow-hidden group-hover:scale-105 transition-transform">
                  <span className="text-2xl font-bold opacity-30 text-primary">{restaurant.name.charAt(0)}</span>
                </div>
                <div className="flex-1 overflow-hidden">
                  <h3 className="font-bold text-sm truncate">{restaurant.name}</h3>
                  <p className="text-xs text-muted-foreground truncate">{restaurant.description}</p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
                    <span className="flex items-center gap-1">
                      <Star className="h-3 w-3 text-yellow-500" />
                      {restaurant.rating}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      20-35 min
                    </span>
                  </div>
                </div>
              </GlassCard>
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
