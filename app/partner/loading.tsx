import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Loader2 } from "lucide-react"

export default function Loading() {
  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Partner Dashboard" 
          description="Manage your jobs"
        />
      </div>
      <div className="space-y-4">
        <div className="h-6 w-32 bg-primary/20 animate-pulse rounded"></div>
        <div className="grid gap-4 sm:grid-cols-2">
          <GlassCard className="p-8 h-48 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </GlassCard>
          <GlassCard className="p-8 h-48 hidden sm:flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
