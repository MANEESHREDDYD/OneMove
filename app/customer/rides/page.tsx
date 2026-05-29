import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"

export default function CustomerRides() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Request a Ride" 
        description="Where are you heading today?"
      />
      <GlassCard className="p-8">
        <h2 className="text-xl font-bold">Ride Map</h2>
        <p className="text-muted-foreground mt-2">Placeholder for map UI and location picker.</p>
      </GlassCard>
    </div>
  )
}
