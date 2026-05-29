import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"

export default function CustomerOrders() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Your Orders" 
        description="Track your active orders and view past history."
      />
      <GlassCard className="p-8">
        <h2 className="text-xl font-bold">Order History</h2>
        <p className="text-muted-foreground mt-2">Placeholder for past and current orders.</p>
      </GlassCard>
    </div>
  )
}
