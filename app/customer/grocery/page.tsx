import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"

export default function CustomerGrocery() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Grocery Delivery" 
        description="Fresh groceries delivered to your door."
      />
      <GlassCard className="p-8">
        <h2 className="text-xl font-bold">Stores near you</h2>
        <p className="text-muted-foreground mt-2">Placeholder for grocery store listings.</p>
      </GlassCard>
    </div>
  )
}
