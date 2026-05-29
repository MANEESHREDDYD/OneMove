import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"

export default function CustomerEats() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Food Delivery" 
        description="Craving something? We'll deliver it fast."
      />
      <GlassCard className="p-8">
        <h2 className="text-xl font-bold">Restaurants near you</h2>
        <p className="text-muted-foreground mt-2">Placeholder for restaurant listings.</p>
      </GlassCard>
    </div>
  )
}
