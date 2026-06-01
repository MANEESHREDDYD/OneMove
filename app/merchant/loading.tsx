import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Loader2 } from "lucide-react"

export default function Loading() {
  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Merchant Portal" 
          description="Manage your store and incoming orders"
        />
      </div>
      <div className="grid gap-4 md:grid-cols-3 mb-8">
        {[1, 2, 3].map((i) => (
          <GlassCard key={i} className="p-6 h-32 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-primary" />
          </GlassCard>
        ))}
      </div>
      <div className="space-y-4">
        <div className="h-6 w-32 bg-primary/20 animate-pulse rounded"></div>
        <GlassCard className="h-64 flex items-center justify-center">
           <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </GlassCard>
      </div>
    </div>
  )
}
